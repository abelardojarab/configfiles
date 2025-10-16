class services {
  kmod::load {'br_netfilter':
    ensure => present,
  }

  kmod::load {'overlay':
    ensure => present,
  }

  sysctl {'net.ipv4.ip_forward':
    value => 1,
  }
}
