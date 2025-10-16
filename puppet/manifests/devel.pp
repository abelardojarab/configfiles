include apt

class devel {
  # Ensure we can add components/PPAs
  package { 'software-properties-common': ensure => installed } ->

  # Enable universe/multiverse once (idempotent)
  exec { 'enable-universe':
    command => '/usr/bin/add-apt-repository -y universe',
    unless  => 'grep -E "^[^#].*universe" /etc/apt/sources.list',
    path    => ['/usr/bin','/bin'],
  } ->
  exec { 'enable-multiverse':
    command => '/usr/bin/add-apt-repository -y multiverse',
    unless  => 'grep -E "^[^#].*multiverse" /etc/apt/sources.list',
    path    => ['/usr/bin','/bin'],
  } ~> Class['apt::update']

  # Building tools
  package { ['build-essential', 'cmake', 'git', 'git-lfs', 'gcc', "meson", "ninja-build"]:
    ensure => installed,
  }

  # Network
  package { ['rsync', 'wget', 'curl', 'net-tools']:
    ensure => installed,
  }

  # Libraries
  package { ["libmysqlclient-dev", "libmunge-dev", "zlib1g-dev", "libssl-dev",
             "libvterm-dev", "libyaml-dev", "libsqlite3-dev",
             "libxml2-dev", "libelf-dev", "libjsoncpp-dev", "libunwind-dev",
             "libdrm-dev", "qtdeclarative5-dev", "libpci-dev", "qtbase5-dev",
             "libbpfcc-dev", "libpng-dev", "libpoppler-glib-dev",
             "libjansson-dev", "libgccjit-11-dev", "libprotoc-dev",
             "libevent-dev", "libjemalloc-dev", "libslurm-dev",
             "libsystemd-dev", "libudev-dev", "libgettextpo-dev", "libnuma-dev",
             "libprotobuf-dev", "libpcre2-dev", "libluajit-5.1-dev",
             "liblua5.1.0-dev", "libhdf5-dev", "libftdi-dev", "libusb-dev",
             "libgtk-3-dev", "libgnutls28-dev", "libtiff5-dev", "libgif-dev",
             "libjpeg-dev", "libxpm-dev", "libturbojpeg0-dev",
             "libfreetype6-dev", "libfontconfig1-dev", "libx11-dev",
             "libxinerama-dev", "libxcursor-dev", "mesa-common-dev",
             "libglu1-mesa-dev", "libxrandr-dev", "libncurses-dev", "texinfo",
             "libmpich-dev", "libopenmpi-dev",
             "libenchant-2-dev", "libopencv-dev", "libusb-1.0-0-dev",
             "libavcodec-dev", "libavformat-dev", "libswscale-dev",
             "libresample-dev", "libgstreamer1.0-dev",
             "libgstreamer-plugins-base1.0-dev", "libxvidcore-dev",
             "libx264-dev", "libfaac-dev", "libmp3lame-dev", "libtheora-dev",
             "libopencore-amrnb-dev", "libopencore-amrwb-dev", "libv4l-dev",
             "libxine2-dev", "libeigen3-dev"]:
               ensure => installed,
  }

  # Packages
  package { ["sysstat", "mysql-server", "mysql-client", "pgcli", "axel",
             "ripgrep", "gdb", "openssl", "munge", "p7zip-full",
             "feh", "sysbench", "hardinfo", "stress-ng",
             "smartmontools", "silversearcher-ag", "gsmartcontrol", "preload",
             "zlib1g", "sqlite3", "clangd", "clang-tidy", "clang", "rustc",
             "cargo", "clang-format", "cppcheck", "neofetch", "ncdu", "nnn",
             "elinks", "w3m", "mutt", "autoconf", "libc6-dev", "automake",
             "libtool", "bison", "cmake-curses-gui", "pkg-config", "clinfo",
             "vulkan-tools", "vainfo", "gettext", "mesa-opencl-icd", "samba",
             "nfs-common", "gnupg2", "pass", "avahi-daemon", "avahi-discover",
             "avahi-dnsconfd", "avahi-utils", "libnss-mdns", "mdns-scan",
             "nfs-kernel-server", "libjansson4", "pydf", "exuberant-ctags",
             "global", "libtree-sitter0", "libtree-sitter-dev",
             "fzf", "bat", "fd-find", "finch", "gnuplot", "ffmpeg",
             "linux-firmware", "bpfcc-tools", "linux-tools-generic",
             "libpoppler-private-dev", "elpa-pdf-tools-server", "chromium-browser",
             "chromium-chromedriver", "multitime", "iperf", "plantuml",
             "protobuf-compiler", "libjpeg9", "libgccjit0", "cpu-checker",
             "ovmf", "zsync", "libjpeg-progs", "pdfgrep", "jq",
             "ttygif", "sshpass", "htop", "device-tree-compiler", "libfdt1",
             "lzop", "u-boot-tools", "chrpath", "xz-utils", "i2c-tools",
             "calibre", "calibre-bin", "openmpi-bin", "x264", "v4l-utils",
             "gnome-startup-applications"]:
               ensure => installed,
  }
}
