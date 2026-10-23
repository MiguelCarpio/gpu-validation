# gpu-validation

## Running manually
Once the RHOSO setup is complete, do the following:

1. Clone the repository
    ```
    git clone git@github.com:rhos-vaf/gpu-validation.git
    cd gpu-validation/
    ```
1. (Optional - see NOTE below) Create a credentials file for registry login using a token. You can generate one at [here](https://access.redhat.com/terms-based-registry/) after logging in.

    NOTE - If not providing registry credentials, you must disable model tests with `-e gpu_validation_model_tests_enabled=false`

    creds.yaml
    ```
    gpu_validation_model_download_registry_username: "|3c5aa7e0-9bb9...."
    gpu_validation_model_download_registry_password: "eyJhbGciOiJSUzUxMiJ9...."
    ```
1. Set up and test your access to RHOSO
    ```
    oc cp openstackclient:.config/openstack/ ~/.config/openstack
    oc cp openstackclient:/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem ./tls-ca-bundle.pem
    export OS_CLOUD=default
    openstack --os-cacert ./tls-ca-bundle.pem flavor list
    ```
1. Install Ansible dependencies
    ```
    ansible-galaxy install -r requirements.yaml
    ```
1. Run it (requires ansible-core>=2.15)
    ```
    JUNIT_OUTPUT_DIR=./ ansible-playbook -i inventory main.yaml -e @vars.yaml -e @creds.yaml -e '{"gpu_validation_pci_devices":{"10de:20f1": 1}}'
    ```

## Running w/ test-operator

1. Confirm that your RHOSO deployment has test-operator running
    ```
    $ oc get deploy -n openstack-operators test-operator-controller-manager
    NAME                               READY   UP-TO-DATE   AVAILABLE   AGE
    test-operator-controller-manager   1/1     1            1           29d
    ```
1. Adjust the `gpu_validation_pci_devices` variable in AnsibleTestCR.yaml to match your hardware
1. Launch the test container
    ```
    $ oc apply -f AnsibleTestCR.yaml
    ```

## Stability / lifecycle testing

Two optional, independent loops exercise GPU reliability across VM lifecycles
(reboots and full recreation). Both are off by default.

### Guest reboot stability (`stability_guest`)

Reboots the same target VM N times and re-asserts the GPU each cycle: `lspci`
presence, `nvidia-smi` (and MIG mode when `gpu_validation_mode: mig`), the CUDA
sanity check, plus a guest `dmesg` scan for GPU faults (`Xid`, `NVRM`, "fallen off
the bus", etc.). It catches GPUs that do not survive a guest reboot/FLR.

Enable it via vars:

```yaml
gpu_validation_stability_guest_enabled: true
gpu_validation_stability_guest_cycles: 3
```

CLI:

```
ansible-playbook -i inventory main.yaml -e @vars.yaml \
  -e gpu_validation_stability_guest_enabled=true \
  -e gpu_validation_stability_guest_cycles=3
```

### Lifecycle reclaim (`lifecycle_reclaim`)

Behind `gpu_validation_lifecycle_reclaim_enabled` (default `false`), a dedicated
control-node play loops: create VM → verify the GPU in the guest (`nvidia-smi`) →
delete VM → assert each GPU PCI BDF returns to the expected host driver on the
**compute node** (no device leak) and scan the compute-node `dmesg` for
`vfio`/IOMMU/NVIDIA faults. The expected host driver is derived from
`gpu_validation_mode` (`vfio-pci` for `pci_passthrough`, `nvidia` for `mig`/`vgpu`).
It runs its own create/delete cycles, independent of the main validation VM, and
each cycle rebuilds a whole VM — so keep the cycle count small.

Enable and configure via vars:

```yaml
gpu_validation_lifecycle_reclaim_enabled: true
gpu_validation_lifecycle_reclaim_cycles: 3
gpu_validation_lifecycle_reclaim_gpu_bdfs:
  - "0000:18:00.0"
  - "0000:67:00.0"
```

CLI:

```
ansible-playbook -i inventory main.yaml -e @vars.yaml \
  -e gpu_validation_lifecycle_reclaim_enabled=true \
  -e gpu_validation_lifecycle_reclaim_cycles=3 \
  -e '{"gpu_validation_lifecycle_reclaim_gpu_bdfs":["0000:18:00.0","0000:67:00.0"]}'
```
