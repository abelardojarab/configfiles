include apt

class virtualization {
    package { ["vagrant", "vagrant-lxc", "vagrant-libvirt", "vagrant-mutate", "virt-manager", "qemu", "qemu-kvm",
               "qemu-user", "qemu-system-arm", "qemu-system-x86", "gnome-boxes"]:
        ensure => installed,
    }
}
