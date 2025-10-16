class scripts {
  file { '/root/fix_missing_keys.sh':
    ensure   => present,
    source   => 'puppet:///modules/scripts/fix_missing_keys.sh',
    mode     => '0755',
    owner    => 'root',
    group    => 'root',
  } ->
  exec { 'Get the missing GPG keys':
    command  => '/root/fix_missing_keys.sh',
    cwd      => '/root',
    user     => 'root',
  }

  file { '/root/get_gitlab_cert.sh':
    ensure   => present,
    source   => 'puppet:///modules/scripts/get_gitlab_cert.sh',
    mode     => '0755',
    owner    => 'root',
    group    => 'root',
  } ->
  exec { 'Get the Gitlab certificates':
    command  => '/root/get_gitlab_cert.sh',
    cwd      => '/root',
    user     => 'root',
  }

  file { '/root/fix_munge.sh':
    ensure   => present,
    source   => 'puppet:///modules/scripts/fix_munge.sh',
    mode     => '0755',
    owner    => 'root',
    group    => 'root',
  } ->
  exec { 'Fix munge id/gid':
    command  => '/root/fix_munge.sh',
    cwd      => '/root',
    user     => 'root',
  }

  file { '/etc/slurm-llnl/slurm.conf':
    ensure   => present,
    source   => 'puppet:///modules/scripts/slurm.conf',
    mode     => '0644',
    owner    => 'root',
    group    => 'root',
  }

}
