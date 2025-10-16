include apt

class virtualisation {
    apt::ppa { 'ppa:jacob/virtualisation':
    } ->

    apt::ppa { 'ppa:savoury1/virtualisation':
    } ->

    apt::ppa { 'ppa:flexiondotorg/quickemu':
    } ->

    apt::ppa { 'ppa:yannick-mauray/quickgui':
    } ->

    package { ["vagrant", "vagrant-lxc", "vagrant-libvirt", "vagrant-mutate", "virt-manager", "qemu", "qemu-user",
    "qemu-system-arm", "qemu-system-x86", "spice-vdagent", "spice-webdavd", "spice-client-gtk", "gnome-boxes", "quickemu"]:
        ensure => installed,
    }
}
