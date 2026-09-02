class zabbix {
  apt::source { 'zabbix':
    location => 'https://repo.zabbix.com/zabbix/6.0/ubuntu',
    release  => 'focal',   # zabbix has no resolute dist yet
    repos    => 'main',
    key      => {
      name   => 'zabbix.asc',
      source => 'https://repo.zabbix.com/zabbix-official-repo.key',
    },
  }
  ~> Class['apt::update']

  class { 'zabbix::agent':
    server      => '100.78.48.121',
    manage_repo => false,
    require     => Class['apt::update'],
  }
}
