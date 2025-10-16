accounts::user { 'cpulab_farm':
  comment  => 'Lab runner',
  uid      => '4001',
  gid      => '4001',
  shell    => '/bin/bash',
  groups   => ['video', 'kvm', 'lxd', 'docker', 'libvirt', 'libvirt-qemu'],
  password => '$1$R/B8FbE/$yrkr69ILCwXUuOMeFT9N60',
  locked   => false,
}

accounts::user { 'teamcity':
  comment  => 'Teamcity runner',
  uid      => '982',
  gid      => '990',
  shell    => '/usr/sbin/nologin',
  groups   => ['video', 'kvm', 'lxd', 'docker', 'libvirt', 'libvirt-qemu'],
  password => '$1$67kbO6N2$XYm9SP4acsagXpvz/41UD.',
  locked   => false,
}

accounts::user { 'jenkins':
  comment  => 'Jenkins runner',
  uid      => '150',
  gid      => '158',
  shell    => '/usr/sbin/nologin',
  groups   => ['video', 'kvm', 'lxd', 'docker', 'libvirt', 'libvirt-qemu'],
  password => '$1$EVaVA.0a$N5HwBFuhB.7k6ZfNDNaWm.',
  locked   => false,
}
