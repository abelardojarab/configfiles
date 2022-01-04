include apt

class devel {
      exec {'apt-update':
          command => "/usr/bin/apt-get update",
          refreshonly => true,
      } ->

      package { ["mysql-client", "mysql-server", "libmysqlclient-dev", "git", "build-essential", "openssl",
                "zlib1g", "zlib1g-dev", "libssl-dev", "libyaml-dev", "libsqlite3-dev", "sqlite3", "libxml2-dev", "autoconf", "wget", "curl", "git-lfs",
                "libc6-dev", "automake", "libtool", "bison", "cmake", "pkg-config"]:
          ensure => installed,
          require => Exec['apt-update']
      }
}
