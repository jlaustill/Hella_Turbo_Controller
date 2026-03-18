# Hella Actuator EEPROM Comparison

## Units
- **G-222**: From user's original actuator (eeprom_backup.bin)
- **G-221 (downloaded)**: Downloaded from internet (G-221.bin)
- **G-221 (actual)**: Dumped from user's physical G-221 unit (G-221-actual.bin)
- **G-277**: No dump available (unit had no CAN communication)

## EEPROM Structure
- 128 bytes total
- Two-half structure: 0x00-0x3F and 0x40-0x7F
- First half (0x00-0x3F): Active configuration
- Second half (0x40-0x7F): Mirror/backup, with factory calibration at 0x4F-0x5F
- Addresses 0x0F-0x1F: Write-protected, managed by actuator firmware

## CAN ID Encoding
CAN IDs are stored across two bytes:
- **High byte**: `CAN_ID >> 3` (upper 8 bits of 11-bit CAN ID)
- **Low byte bits 7-5**: `(CAN_ID & 0x07) << 5` (lower 3 bits of CAN ID)
- **Low byte bits 4-0**: Frame DLC configuration (0x08 = 8-byte frames, 0x00 = zero-length frames)

Decode CAN ID: `high_byte * 8 + (low_byte >> 5)`

**Confirmed: The lower 5 bits of the low byte directly control CAN frame DLC (0=0 bytes, 8=8 bytes).**
Tested values 0-8: each produces exactly that many bytes in the broadcast frame. Must be 0x08 for normal 8-byte operation.

## Byte Map

| Addr      | G-221 dl   | G-221 act   | G-222 act   | G-277 act   | Confirmed Use                  | Suspected Use                          | Comments                                                            |
| --------- | ---------- | ----------- | ----------- | ----------- | ------------------------------ | -------------------------------------- | ------------------------------------------------------------------- |
| 0x00(0)   | 0x07(7  )  | 0x05(5  )   | 0x05(5  )   |             |                                | Device ID high byte                    | Differs per unit, same between halves                               |
| 0x01(1)   | 0xB2(178)  | 0x1E(30 )   | 0x0E(14 )   |             |                                | Device ID low byte                     | Differs per unit, same between halves                               |
| 0x02(2)   | 0x55(85 )  | 0x55(85 )   | 0x55(85 )   |             |                                |                                        | Same across all units (0x55)                                        |
| 0x03(3)   | 0x00(0  )  | 0x00(0  )   | 0x00(0  )   |             | Min position high byte         |                                        | Written by set_min() in hella_prog.py                               |
| 0x04(4)   | 0x8B(139)  | 0xAA(170)   | 0xAE(174)   |             | Min position low byte          |                                        | Written by set_min() in hella_prog.py                               |
| 0x05(5)   | 0x03(3  )  | 0x02(2  )   | 0x03(3  )   |             | Max position high byte         |                                        | Written by set_max() in hella_prog.py                               |
| 0x06(6)   | 0x23(35 )  | 0xD6(214)   | 0x96(150)   |             | Max position low byte          |                                        | Written by set_max() in hella_prog.py                               |
| 0x07(7)   | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                |                                        | Same across all units (0xFF)                                        |
| 0x08(8)   | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                |                                        | Same across all units (0xFF)                                        |
| 0x09(9)   | 0xCB(203)  | 0xCB(203)   | 0x7D(125)   |             | Programming response CAN ID hi |                                        | G-222=0x3E8, G-221=0x658. Used for EEPROM reads + init responses.   |
| 0x0A(10)  | 0x08(8  )  | 0x08(8  )   | 0x08(8  )   |             | Programming response CAN ID lo |                                        | Bits 7-5=CAN ID, bits 4-0=DLC (confirmed 0-8 = frame bytes)        |
| 0x0B(11)  | 0xCE(206)  | 0xCE(206)   | 0xCE(206)   |             |                                | Shared/diagnostic CAN ID high          | Both units decode to 0x670                                          |
| 0x0C(12)  | 0x0A(10 )  | 0x0A(10 )   | 0x0A(10 )   |             |                                | Shared/diagnostic CAN ID low           | See 0x0B                                                            |
| 0x0D(13)  | 0x01(1  )  | 0x01(1  )   | 0x01(1  )   |             |                                |                                        | Same across all units (0x01)                                        |
| 0x0E(14)  | 0x55(85 )  | 0x55(85 )   | 0x2A(42 )   |             |                                | Config byte                            | G-222=0x2A, both G-221s=0x55                                        |
| 0x0F(15)  | 0x06(6  )  | 0x0C(12 )   | 0x0E(14 )   |             |                                | Actuator-managed                       | Write-protected from CAN, differs per unit                          |
| 0x10(16)  | 0x00(0  )  | 0x00(0  )   | 0x00(0  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x11(17)  | 0x08(8  )  | 0x00(0  )   | 0x00(0  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x12(18)  | 0x00(0  )  | 0x00(0  )   | 0x04(4  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x13(19)  | 0x00(0  )  | 0x08(8  )   | 0x00(0  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x14(20)  | 0x00(0  )  | 0x00(0  )   | 0x04(4  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x15(21)  | 0x08(8  )  | 0x00(0  )   | 0x20(32 )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x16(22)  | 0x00(0  )  | 0x00(0  )   | 0x00(0  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x17(23)  | 0x00(0  )  | 0x08(8  )   | 0x00(0  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x18(24)  | 0x00(0  )  | 0x00(0  )   | 0x04(4  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x19(25)  | 0x00(0  )  | 0x00(0  )   | 0x00(0  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x1A(26)  | 0x00(0  )  | 0x00(0  )   | 0x00(0  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x1B(27)  | 0x00(0  )  | 0x08(8  )   | 0x00(0  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x1C(28)  | 0x00(0  )  | 0x00(0  )   | 0x04(4  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x1D(29)  | 0x00(0  )  | 0x00(0  )   | 0x00(0  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x1E(30)  | 0x00(0  )  | 0x00(0  )   | 0x04(4  )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x1F(31)  | 0x00(0  )  | 0x08(8  )   | 0x20(32 )   |             |                                | Actuator-managed                       | Write-protected (0x0F-0x1F region), changes during motor ops        |
| 0x20(32)  | 0x34(52 )  | 0x34(52 )   | 0x34(52 )   |             |                                |                                        | Same across all units (0x34)                                        |
| 0x21(33)  | 0x15(21 )  | 0x15(21 )   | 0x15(21 )   |             |                                |                                        | Same across all units (0x15)                                        |
| 0x22(34)  | 0xAA(170)  | 0xAA(170)   | 0x00(0  )   |             |                                | Rotation offset                        | Calibrates pos=0 at min endstop. Scale: ~4 units per position count |
| 0x23(35)  | 0x2C(44 )  | 0x22(34 )   | 0x2D(45 )   |             |                                | Config (near range)                    | All three values differ                                             |
| 0x24(36)  | 0x9D(157)  | 0x9D(157)   | 0x00(0  )   |             | Position command CAN ID high   |                                        | G-221=0x4EA, G-222=0x000. Required (with 0x29) for CAN pos ctrl.    |
| 0x25(37)  | 0x48(72 )  | 0x48(72 )   | 0x08(8  )   |             | Position command CAN ID low    |                                        | Bits 7-5=CAN ID, bits 4-0=DLC (confirmed 0-8 = frame bytes)        |
| 0x26(38)  | 0x06(6  )  | 0x06(6  )   | 0x00(0  )   |             | Command format register        |                                        | 0x06=16-bit (2-byte) commands, 0x00=8-bit (1-byte 0-250) commands   |
| 0x27(39)  | 0x9D(157)  | 0x9D(157)   | 0xCB(203)   |             | Position broadcast CAN ID high |                                        | G-222=0x658, G-221=0x4EB. Encoding: byte*8+(next_byte>>5)           |
| 0x28(40)  | 0x68(104)  | 0x68(104)   | 0x08(8  )   |             | Position broadcast CAN ID low  |                                        | Bits 7-5=CAN ID, bits 4-0=DLC (confirmed 0-8 = frame bytes)        |
| 0x29(41)  | 0x2A(42 )  | 0x2A(42 )   | 0x62(98 )   |             |                                | Mode register                          | Enum, not bitmask. 0x62/0x2A/0x00 accepted, 0x72/0x6A rejected.     |
| 0x2A(42)  | 0xA0(160)  | 0xA0(160)   | 0xA0(160)   |             |                                |                                        | Same across all units (0xA0)                                        |
| 0x2B(43)  | 0x96(150)  | 0x96(150)   | 0x96(150)   |             |                                |                                        | Same across all units (0x96)                                        |
| 0x2C(44)  | 0x32(50 )  | 0x32(50 )   | 0x06(6  )   |             |                                | Config byte                            | G-221s=0x32, G-222=0x06                                             |
| 0x2D(45)  | 0x02(2  )  | 0x02(2  )   | 0x02(2  )   |             |                                |                                        | Same across all units (0x02)                                        |
| 0x2E(46)  | 0x1F(31 )  | 0x1F(31 )   | 0x1D(29 )   |             |                                | Config byte                            | G-221s=0x1F, G-222=0x1D                                             |
| 0x2F(47)  | 0x09(9  )  | 0x09(9  )   | 0x09(9  )   |             |                                |                                        | Same across all units (0x09)                                        |
| 0x30(48)  | 0x00(0  )  | 0x00(0  )   | 0x00(0  )   |             |                                |                                        | Same across all units (0x00)                                        |
| 0x31(49)  | 0x2C(44 )  | 0x2D(45 )   | 0x2A(42 )   |             |                                | Config byte                            | All three values differ slightly                                    |
| 0x32(50)  | 0x03(3  )  | 0x03(3  )   | 0x03(3  )   |             |                                |                                        | Same across all units (0x03)                                        |
| 0x33(51)  | 0xD3(211)  | 0xD1(209)   | 0xD5(213)   |             |                                | Config byte                            | All three values differ slightly                                    |
| 0x34(52)  | 0x00(0  )  | 0x00(0  )   | 0x00(0  )   |             |                                |                                        | Same across all units (0x00)                                        |
| 0x35(53)  | 0x00(0  )  | 0x02(2  )   | 0x00(0  )   |             |                                |                                        | G-221 actual=0x02, others=0x00                                      |
| 0x36(54)  | 0x20(32 )  | 0x20(32 )   | 0x20(32 )   |             |                                |                                        | Same across all units (0x20)                                        |
| 0x37(55)  | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                |                                        | Same across all units (0xFF)                                        |
| 0x38(56)  | 0x40(64 )  | 0x40(64 )   | 0x20(32 )   |             |                                | Config byte                            | G-221s=0x40, G-222=0x20                                             |
| 0x39(57)  | 0x20(32 )  | 0x20(32 )   | 0x20(32 )   |             |                                |                                        | Same across all units (0x20)                                        |
| 0x3A(58)  | 0x0A(10 )  | 0x0A(10 )   | 0x0A(10 )   |             |                                |                                        | Same across all units (0x0A)                                        |
| 0x3B(59)  | 0x52(82 )  | 0x52(82 )   | 0x54(84 )   |             |                                | Config byte                            | G-221s=0x52, G-222=0x54                                             |
| 0x3C(60)  | 0x01(1  )  | 0x01(1  )   | 0x01(1  )   |             |                                |                                        | Same across all units (0x01)                                        |
| 0x3D(61)  | 0x8E(142)  | 0x8E(142)   | 0x8E(142)   |             |                                |                                        | Same across all units (0x8E)                                        |
| 0x3E(62)  | 0x01(1  )  | 0x01(1  )   | 0x01(1  )   |             |                                |                                        | Same across all units (0x01)                                        |
| 0x3F(63)  | 0xB0(176)  | 0xAE(174)   | 0xAC(172)   |             |                                | Config byte                            | All three values differ slightly                                    |
| 0x40(64)  | 0x07(7  )  | 0x05(5  )   | 0x05(5  )   |             |                                | Mirror: Device ID high                 | Mirrors 0x00                                                        |
| 0x41(65)  | 0xB2(178)  | 0x1E(30 )   | 0x0E(14 )   |             |                                | Mirror: Device ID low                  | Mirrors 0x01                                                        |
| 0x42(66)  | 0x55(85 )  | 0x55(85 )   | 0x55(85 )   |             |                                |                                        | Mirrors 0x02 (0x55)                                                 |
| 0x43(67)  | 0x00(0  )  | 0x00(0  )   | 0x00(0  )   |             |                                | Mirror: Min position high              | Mirrors 0x03                                                        |
| 0x44(68)  | 0x8B(139)  | 0xAA(170)   | 0xAE(174)   |             |                                | Mirror: Min position low               | Mirrors 0x04                                                        |
| 0x45(69)  | 0x03(3  )  | 0x02(2  )   | 0x03(3  )   |             |                                | Mirror: Max position high              | Mirrors 0x05                                                        |
| 0x46(70)  | 0x23(35 )  | 0xD6(214)   | 0x96(150)   |             |                                | Mirror: Max position low               | Mirrors 0x06                                                        |
| 0x47(71)  | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                |                                        | Mirrors 0x07 (0xFF)                                                 |
| 0x48(72)  | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                |                                        | Mirrors 0x08 (0xFF)                                                 |
| 0x49(73)  | 0xCB(203)  | 0xCB(203)   | 0x7D(125)   |             |                                | Mirror: Programming response CAN ID hi | Mirrors 0x09                                                        |
| 0x4A(74)  | 0x08(8  )  | 0x08(8  )   | 0x08(8  )   |             |                                | Mirror: Programming response CAN ID lo | Mirrors 0x0A. Lower 5 bits = DLC config.                            |
| 0x4B(75)  | 0xCE(206)  | 0xCE(206)   | 0xCE(206)   |             |                                | Mirror: Shared CAN ID high             | Mirrors 0x0B                                                        |
| 0x4C(76)  | 0x0A(10 )  | 0x0A(10 )   | 0x0A(10 )   |             |                                | Mirror: Shared CAN ID low              | Mirrors 0x0C                                                        |
| 0x4D(77)  | 0x01(1  )  | 0x01(1  )   | 0x01(1  )   |             |                                |                                        | Mirrors 0x0D (0x01)                                                 |
| 0x4E(78)  | 0x55(85 )  | 0x55(85 )   | 0x2A(42 )   |             |                                | Mirror: Config byte                    | Mirrors 0x0E                                                        |
| 0x4F(79)  | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                | Factory calibration                    | Second half 0x4F-0x5F differs per unit, not user-writable           |
| 0x50(80)  | 0xA4(164)  | 0xD3(211)   | 0x45(69 )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x51(81)  | 0xA4(164)  | 0xD3(211)   | 0x45(69 )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x52(82)  | 0x10(16 )  | 0x10(16 )   | 0x10(16 )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x53(83)  | 0x2F(47 )  | 0x08(8  )   | 0x2E(46 )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x54(84)  | 0xDB(219)  | 0x8D(141)   | 0x5B(91 )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x55(85)  | 0x00(0  )  | 0x00(0  )   | 0x00(0  )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x56(86)  | 0xD0(208)  | 0xA0(160)   | 0x5E(94 )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x57(87)  | 0x03(3  )  | 0x01(1  )   | 0x09(9  )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x58(88)  | 0x5C(92 )  | 0x6A(106)   | 0xBA(186)   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x59(89)  | 0x71(113)  | 0x71(113)   | 0x71(113)   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x5A(90)  | 0x21(33 )  | 0x21(33 )   | 0x21(33 )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x5B(91)  | 0x22(34 )  | 0x22(34 )   | 0x22(34 )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x5C(92)  | 0x21(33 )  | 0x21(33 )   | 0x22(34 )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x5D(93)  | 0x00(0  )  | 0x00(0  )   | 0x01(1  )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x5E(94)  | 0x15(21 )  | 0x56(86 )   | 0x61(97 )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x5F(95)  | 0x0E(14 )  | 0x08(8  )   | 0x05(5  )   |             |                                | Factory calibration                    | Differs per unit, likely factory-set. Not mirrored from first half. |
| 0x60(96)  | 0x34(52 )  | 0x34(52 )   | 0x34(52 )   |             |                                |                                        | Mirrors 0x20 (0x34)                                                 |
| 0x61(97)  | 0x15(21 )  | 0x15(21 )   | 0x15(21 )   |             |                                |                                        | Mirrors 0x21 (0x15)                                                 |
| 0x62(98)  | 0xAA(170)  | 0xAA(170)   | 0x00(0  )   |             |                                | Mirror: Rotation offset                | Mirrors 0x22                                                        |
| 0x63(99)  | 0x2C(44 )  | 0x22(34 )   | 0x2D(45 )   |             |                                | Mirror: Config                         | Mirrors 0x23                                                        |
| 0x64(100) | 0x9D(157)  | 0x9D(157)   | 0x00(0  )   |             |                                | Mirror: Position command CAN ID high   | Mirrors 0x24. Must be written with 0x24.                            |
| 0x65(101) | 0x48(72 )  | 0x48(72 )   | 0x08(8  )   |             |                                | Mirror: Position command CAN ID low    | Mirrors 0x25. Lower 5 bits = DLC config.                            |
| 0x66(102) | 0x06(6  )  | 0x06(6  )   | 0x00(0  )   |             |                                | Mirror: Command format register        | Mirrors 0x26                                                        |
| 0x67(103) | 0x9D(157)  | 0x9D(157)   | 0xCB(203)   |             |                                | Mirror: Position broadcast CAN ID high | Mirrors 0x27                                                        |
| 0x68(104) | 0x68(104)  | 0x68(104)   | 0x08(8  )   |             |                                | Mirror: Position broadcast CAN ID low  | Mirrors 0x28. Lower 5 bits = DLC config.                            |
| 0x69(105) | 0x2A(42 )  | 0x2A(42 )   | 0x62(98 )   |             |                                | Mirror: Mode register                  | Mirrors 0x29. Enum, not bitmask.                                    |
| 0x6A(106) | 0xA0(160)  | 0xA0(160)   | 0xA0(160)   |             |                                |                                        | Mirrors 0x2A (0xA0)                                                 |
| 0x6B(107) | 0x96(150)  | 0x96(150)   | 0x96(150)   |             |                                |                                        | Mirrors 0x2B (0x96)                                                 |
| 0x6C(108) | 0x32(50 )  | 0x32(50 )   | 0x06(6  )   |             |                                | Mirror: Config byte                    | Mirrors 0x2C                                                        |
| 0x6D(109) | 0x02(2  )  | 0x02(2  )   | 0x02(2  )   |             |                                |                                        | Mirrors 0x2D (0x02)                                                 |
| 0x6E(110) | 0x1F(31 )  | 0x1F(31 )   | 0x1D(29 )   |             |                                | Mirror: Config byte                    | Mirrors 0x2E                                                        |
| 0x6F(111) | 0x09(9  )  | 0x09(9  )   | 0x09(9  )   |             |                                |                                        | Mirrors 0x2F (0x09)                                                 |
| 0x70(112) | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                |                                        | All 0xFF in all units                                               |
| 0x71(113) | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                |                                        | All 0xFF in all units                                               |
| 0x72(114) | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                |                                        | All 0xFF in all units                                               |
| 0x73(115) | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                |                                        | All 0xFF in all units                                               |
| 0x74(116) | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                |                                        | All 0xFF in all units                                               |
| 0x75(117) | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                |                                        | All 0xFF in all units                                               |
| 0x76(118) | 0x20(32 )  | 0x20(32 )   | 0x20(32 )   |             |                                |                                        | Mirrors 0x36 (0x20)                                                 |
| 0x77(119) | 0xFF(255)  | 0xFF(255)   | 0xFF(255)   |             |                                |                                        | Mirrors 0x37 (0xFF)                                                 |
| 0x78(120) | 0x40(64 )  | 0x40(64 )   | 0x20(32 )   |             |                                | Mirror: Config byte                    | Mirrors 0x38                                                        |
| 0x79(121) | 0x20(32 )  | 0x20(32 )   | 0x20(32 )   |             |                                |                                        | Mirrors 0x39 (0x20)                                                 |
| 0x7A(122) | 0x0A(10 )  | 0x0A(10 )   | 0x0A(10 )   |             |                                |                                        | Mirrors 0x3A (0x0A)                                                 |
| 0x7B(123) | 0x52(82 )  | 0x52(82 )   | 0x54(84 )   |             |                                | Mirror: Config byte                    | Mirrors 0x3B                                                        |
| 0x7C(124) | 0x01(1  )  | 0x01(1  )   | 0x01(1  )   |             |                                |                                        | Mirrors 0x3C (0x01)                                                 |
| 0x7D(125) | 0x8E(142)  | 0x8E(142)   | 0x8E(142)   |             |                                |                                        | Mirrors 0x3D (0x8E)                                                 |
| 0x7E(126) | 0x01(1  )  | 0x01(1  )   | 0x01(1  )   |             |                                |                                        | Mirrors 0x3E (0x01)                                                 |
| 0x7F(127) | 0xB0(176)  | 0xAE(174)   | 0xAC(172)   |             |                                | Mirror: Config byte                    | Mirrors 0x3F                                                        |
