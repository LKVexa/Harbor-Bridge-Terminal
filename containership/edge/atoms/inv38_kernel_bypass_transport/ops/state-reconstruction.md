# State reconstruction & backup (INV-38-C095)

Every mutable state class is classified reconstructible vs persistent. MR keys,
queue handles and device-local tokens are never restored across reboot/device
reset — they are recreated and rebound (see C057). Reconstructible state is
rebuilt from authoritative external inputs starting from an empty node to a
verified healthy state; the procedure is modelled and tested in
`tests/recovery/test_reconstruction.py`. **Status:** `IN_PROGRESS` — device-
replacement rebuild needs hardware.
