import os
from conans import ConanFile, CMake, AutoToolsBuildEnvironment, tools
from conans.tools import os_info, SystemPackageTool, download, untargz, replace_in_file, unzip

class ConanRecipe(ConanFile):
    name = "portaudio"
    version = "v190600.20161030"
    settings = "os", "compiler", "build_type", "arch"
    generators = ["cmake", "txt"]
    sources_folder = "sources"
    description = "Conan package for the Portaudio library"
    url = "https://github.com/jgsogo/conan-portaudio"
    license = "http://www.portaudio.com/license.html"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {'shared': False, 'fPIC': True}
    exports = ["FindPortaudio.cmake", "CMakeLists.txt"]

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd
        if self.settings.os == "Windows":
            self.options.remove("fPIC")

    def system_requirements(self):
        if os_info.is_linux:
            if os_info.with_apt:
                installer = SystemPackageTool()
                if self.settings.arch == "x86" and tools.detected_architecture() == "x86_64":
                    arch_suffix = ':i386'
                    installer.install("g++-multilib")
                else:
                    arch_suffix = ''
                installer.install("%s%s" % ("libasound2-dev", arch_suffix))
                installer.install("%s%s" % ("libjack-dev", arch_suffix))
            elif os_info.with_yum:
                installer = SystemPackageTool()
                if self.settings.arch == "x86" and tools.detected_architecture() == "x86_64":
                    arch_suffix = '.i686'
                    installer.install("glibmm24.i686")
                    installer.install("glibc-devel.i686")
                else:
                    arch_suffix = ''
                installer.install("%s%s" % ("alsa-lib-devel", arch_suffix))
                installer.install("%s%s" % ("jack-audio-connection-kit-devel", arch_suffix))

    def source(self):
        zip_name = 'portaudio_%s' % self.version
        if self.version == 'master':
            self.run('mkdir %s' % self.sources_folder)
            zip_name += '.zip'
            download('https://app.assembla.com/spaces/portaudio/git/source/master?_format=zip', '%s/%s' % (self.sources_folder, zip_name))
            unzip('%s/%s' % (self.sources_folder, zip_name), '%s/' % self.sources_folder)
            os.unlink('%s/%s' % (self.sources_folder, zip_name))
        else:
            zip_name += '.tgz'
            download('http://portaudio.com/archives/pa_stable_%s.tgz' % self.version.replace('.','_'), zip_name)
            untargz(zip_name)
            os.unlink(zip_name)
            os.rename("portaudio", self.sources_folder)

        if self.settings.os != "Windows":
            self.run("chmod +x ./%s/configure" % self.sources_folder)

    def patch_source(self):
        if self.settings.os == "Macos":
            replace_in_file(os.path.join(self.sources_folder, "configure"), 'mac_sysroot="-isysroot `xcodebuild -version -sdk macosx10.12 Path`"',
"""
mac_sysroot="-isysroot `xcodebuild -version -sdk macosx10.12 Path`"
elif xcodebuild -version -sdk macosx10.13 Path >/dev/null 2>&1 ; then
                 mac_version_min="-mmacosx-version-min=10.4"
                 mac_sysroot="-isysroot `xcodebuild -version -sdk macosx10.13 Path`"
elif xcodebuild -version -sdk macosx10.14 Path >/dev/null 2>&1 ; then
                 mac_version_min="-mmacosx-version-min=10.4"
                 mac_sysroot="-isysroot `xcodebuild -version -sdk macosx10.14 Path`"
elif xcodebuild -version -sdk macosx10.15 Path >/dev/null 2>&1 ; then
                 mac_version_min="-mmacosx-version-min=10.4"
                 mac_sysroot="-isysroot `xcodebuild -version -sdk macosx10.15 Path`"
"""
                        )
            replace_in_file(os.path.join(self.sources_folder, "configure"), "Could not find 10.5 to 10.12 SDK.", "Could not find 10.5 to 10.15 SDK.")
        elif self.settings.os == "Windows" and self.settings.compiler == "gcc":
            replace_in_file(os.path.join(self.sources_folder, "CMakeLists.txt"), 'OPTION(PA_USE_WDMKS "Enable support for WDMKS" ON)', 'OPTION(PA_USE_WDMKS "Enable support for WDMKS" OFF)')
            replace_in_file(os.path.join(self.sources_folder, "CMakeLists.txt"), 'OPTION(PA_USE_WDMKS_DEVICE_INFO "Use WDM/KS API for device info" ON)', 'OPTION(PA_USE_WDMKS_DEVICE_INFO "Use WDM/KS API for device info" OFF)')
            replace_in_file(os.path.join(self.sources_folder, "CMakeLists.txt"), 'OPTION(PA_USE_WASAPI "Enable support for WASAPI" ON)', 'OPTION(PA_USE_WASAPI "Enable support for WASAPI" OFF)')


    def build(self):
        self.patch_source()

        if self.settings.os == "Linux" or self.settings.os == "Macos":
            env = AutoToolsBuildEnvironment(self)
            with tools.environment_append(env.vars):
                env.fpic = self.options.fPIC
                with tools.environment_append(env.vars):
                    command = ''
                    if self.settings.os == "Macos" and self.settings.compiler == "apple-clang":
                        command = './configure --disable-mac-universal && make'
                    else:
                        command = './configure && make'
                    self.run("cd %s && %s" % (self.sources_folder, command))
            if self.settings.os == "Macos" and self.options.shared:
                self.run('cd %s/lib/.libs && for filename in *.dylib; do install_name_tool -id $filename $filename; done' % self.sources_folder)
        else:
            cmake = CMake(self)
            cmake.definitions["MSVS"] = self.settings.compiler == "Visual Studio"
            cmake.configure()
            cmake.build()

    def package(self):
        self.copy("FindPortaudio.cmake", ".", ".")
        self.copy("*.h", dst="include", src=os.path.join(self.sources_folder, "include"))
        self.copy(pattern="LICENSE*", dst="licenses", src=self.sources_folder,  ignore_case=True, keep_path=False)

        if self.settings.os == "Windows":
            if self.settings.compiler == "Visual Studio":
                self.copy(pattern="*.lib", dst="lib", keep_path=False)
                if self.options.shared:
                    self.copy(pattern="*.dll", dst="bin", keep_path=False)
                self.copy(pattern="*.pdb", dst="bin", keep_path=False)
            else:
                if self.options.shared:
                    self.copy(pattern="*.dll.a", dst="lib", keep_path=False)
                    self.copy(pattern="*.dll", dst="bin", keep_path=False)
                else:
                    self.copy(pattern="*static.a", dst="lib", keep_path=False)

        else:
            if self.options.shared:
                if self.settings.os == "Macos":
                    self.copy(pattern="*.dylib", dst="lib", src=os.path.join(self.sources_folder, "lib", ".libs"))
                else:
                    self.copy(pattern="*.so*", dst="lib", src=os.path.join(self.sources_folder, "lib", ".libs"))
            else:
                self.copy("*.a", dst="lib", src=os.path.join(self.sources_folder, "lib", ".libs"))


    def package_info(self):
        base_name = "portaudio"
        if self.settings.os == "Windows":
            if not self.options.shared:
                base_name += "_static"

            if self.settings.compiler == "Visual Studio":
                base_name += "_x86" if self.settings.arch == "x86" else "_x64"

        elif self.settings.os == "Macos":
            self.cpp_info.exelinkflags.append("-framework CoreAudio -framework AudioToolbox -framework AudioUnit -framework CoreServices -framework Carbon")

        self.cpp_info.libs = [base_name]

        if self.settings.os == "Windows" and self.settings.compiler == "gcc" and not self.options.shared:
            self.cpp_info.libs.append('winmm')

        if self.settings.os == "Linux" and not self.options.shared:
            self.cpp_info.libs.append('jack asound m pthread')
