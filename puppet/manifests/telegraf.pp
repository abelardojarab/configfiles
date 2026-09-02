class telegraf {
  apt::source { 'influxdata':
    location => 'https://repos.influxdata.com/debian',
    release  => 'stable',
    repos    => 'main',
    key      => {
      name   => 'influxdata.gpg',
      # NOTE: the old *_compat.key expired 2026-01-17; this is the current key.
      source => 'https://repos.influxdata.com/influxdata-archive.key',
    },
  }
  ~> Class['apt::update']

  package { 'telegraf':
    ensure  => installed,
    require => Class['apt::update'],
  }

  file { '/etc/telegraf/telegraf.conf':
    ensure  => file,
    content => "# Managed by Puppet - see manifests/telegraf.pp
[global_tags]
  system_name = \"${facts['networking']['hostname']}\"
  cloud_provider = \"NA\"
  build_id = \"NA\"
  instance_type = \"NA\"

[agent]
  interval = \"10s\"
  round_interval = true
  metric_batch_size = 1000
  metric_buffer_limit = 10000
  collection_jitter = \"0s\"
  flush_interval = \"10s\"
  flush_jitter = \"0s\"
  precision = \"0s\"

[[outputs.influxdb]]
  urls = [\"http://100.78.48.121:8086\"]
  database = \"telegrafdb\"
  username = \"cpulab_farm\"
  password = \"cpulab_farm@123\"

[[inputs.cpu]]
  percpu = true
  totalcpu = true
  collect_cpu_time = false
  report_active = false

[[inputs.disk]]
  ignore_fs = [\"tmpfs\", \"devtmpfs\", \"devfs\", \"overlay\", \"aufs\", \"squashfs\"]

[[inputs.diskio]]

[[inputs.kernel]]

[[inputs.mem]]

[[inputs.processes]]

[[inputs.swap]]

[[inputs.system]]
",
    owner   => 'telegraf',
    group   => 'telegraf',
    mode    => '0640',
    require => Package['telegraf'],
    notify  => Service['telegraf'],
  }

  service { 'telegraf':
    ensure  => running,
    enable  => true,
    require => Package['telegraf'],
  }
}
