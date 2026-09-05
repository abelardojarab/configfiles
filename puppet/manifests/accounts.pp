accounts::user { 'cpulab_farm':
  comment  => 'Lab runner',
  uid      => '4001',
  gid      => '4001',
  shell    => '/bin/bash',
  groups   => ['video', 'kvm', 'lxd', 'docker', 'libvirt', 'libvirt-qemu'],
  password => '$1$R/B8FbE/$yrkr69ILCwXUuOMeFT9N60',
  locked   => false,
}

# teamcity's default uid/gid (982/990) is already live on most of the fleet,
# including as the owner of a running TeamCity build agent process on some
# hosts, so it can NOT be renumbered fleet-wide (usermod refuses to touch a
# uid that's in use by a running process, and it would silently orphan any
# group-990-owned files on hosts where only the group gets renamed). Only
# override it on hosts where 982/990 actually collides with an
# auto-assigned system account (fwupd-refresh/render on newer Ubuntu, e.g.
# ubuntu05/26.04) and teamcity has no prior footprint to disrupt.
$teamcity_id_overrides = {
  'ubuntu05' => '6990',
  'ubuntu03' => '6990',
  'ubuntu08' => '6990',
}
$teamcity_id = $teamcity_id_overrides[$facts['networking']['hostname']]

accounts::user { 'teamcity':
  comment  => 'Teamcity runner',
  uid      => pick($teamcity_id, '982'),
  gid      => pick($teamcity_id, '990'),
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
