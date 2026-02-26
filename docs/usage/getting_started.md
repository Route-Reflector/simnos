# Basic Usage
SIMNOS has some built in default hosts which are used in case that no `inventory` is given. In such case it will open the following:

- **router_cisco_ios**: a device with username `user` and password `user` in the port 6000. The platform is `cisco_ios`.
- **router_huawei_smartax**: a device with username `user` and password `user` in the port 6001. The platform is `huawei_smartax`.
- **router_arista_eos**: a device with username `user` and password `user` in the port 6002. The platform is `arista_eos`.

In all cases, the fake devices are running on the localhost or 127.0.0.1 address. To run those just use the following code:

```python
from simnos import SimNOS

network = SimNOS()
network.start()
```

Initiate SSH connection using default username `user` and password `user`:

```bash
ssh -p 6000 user@localhost # cisco_ios
ssh -p 6001 user@localhost # huawei_smartax
```

The equivalent to running above code would be to run SIMNOS CLI without
any arguments:

```bash
simnos
```

!!! warning "Security notice"
    SIMNOS is intended for **testing and development only**. Be aware of the following defaults:

    - **Default credentials**: The built-in inventory uses `user`/`user`. Change these in your inventory for any non-local deployment.
    - **Default SSH host key**: All SIMNOS instances share the same RSA key. An attacker who knows this key can perform MITM attacks. Provide a custom key via `ssh_key_file` in the server configuration for non-local use.
    - **Bind address**: By default SIMNOS binds to `127.0.0.1` (localhost only). In Docker/WSL environments it may bind to `0.0.0.0` (all interfaces), exposing the service to the network.
