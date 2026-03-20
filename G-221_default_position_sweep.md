# G-221 Default Position (0x23) vs Idle Broadcast Sweep

Min=34, Max=989, 0x22=165, 0x26=0x06 (16-bit mode)

Idle broadcast bytes[2:3] report position as 16-bit big-endian.
Below start threshold (0x23=83): reports 0. Above stop threshold (0x23=247): clamps at 997.

| 0x23 | B[2] | B[3] | Position | Notes |
|------|------|------|----------|-------|
|    1 | 0x00 | 0x00 |        0 | clamped at start |
|    2 | 0x00 | 0x00 |        0 | clamped at start |
|    3 | 0x00 | 0x00 |        0 | clamped at start |
|    4 | 0x00 | 0x00 |        0 | clamped at start |
|    5 | 0x00 | 0x00 |        0 | clamped at start |
|    6 | 0x00 | 0x00 |        0 | clamped at start |
|    7 | 0x00 | 0x00 |        0 | clamped at start |
|    8 | 0x00 | 0x00 |        0 | clamped at start |
|    9 | 0x00 | 0x00 |        0 | clamped at start |
|   10 | 0x00 | 0x00 |        0 | clamped at start |
|   11 | 0x00 | 0x00 |        0 | clamped at start |
|   12 | 0x00 | 0x00 |        0 | clamped at start |
|   13 | 0x00 | 0x00 |        0 | clamped at start |
|   14 | 0x00 | 0x00 |        0 | clamped at start |
|   15 | 0x00 | 0x00 |        0 | clamped at start |
|   16 | 0x00 | 0x00 |        0 | clamped at start |
|   17 | 0x00 | 0x00 |        0 | clamped at start |
|   18 | 0x00 | 0x00 |        0 | clamped at start |
|   19 | 0x00 | 0x00 |        0 | clamped at start |
|   20 | 0x00 | 0x00 |        0 | clamped at start |
|   21 | 0x00 | 0x00 |        0 | clamped at start |
|   22 | 0x00 | 0x00 |        0 | clamped at start |
|   23 | 0x00 | 0x00 |        0 | clamped at start |
|   24 | 0x00 | 0x00 |        0 | clamped at start |
|   25 | 0x00 | 0x00 |        0 | clamped at start |
|   26 | 0x00 | 0x00 |        0 | clamped at start |
|   27 | 0x00 | 0x00 |        0 | clamped at start |
|   28 | 0x00 | 0x00 |        0 | clamped at start |
|   29 | 0x00 | 0x00 |        0 | clamped at start |
|   30 | 0x00 | 0x00 |        0 | clamped at start |
|   31 | 0x00 | 0x00 |        0 | clamped at start |
|   32 | 0x00 | 0x00 |        0 | clamped at start |
|   33 | 0x00 | 0x00 |        0 | clamped at start |
|   34 | 0x00 | 0x00 |        0 | clamped at start |
|   35 | 0x00 | 0x00 |        0 | clamped at start |
|   36 | 0x00 | 0x00 |        0 | clamped at start |
|   37 | 0x00 | 0x00 |        0 | clamped at start |
|   38 | 0x00 | 0x00 |        0 | clamped at start |
|   39 | 0x00 | 0x00 |        0 | clamped at start |
|   40 | 0x00 | 0x00 |        0 | clamped at start |
|   41 | 0x00 | 0x00 |        0 | clamped at start |
|   42 | 0x00 | 0x00 |        0 | clamped at start |
|   43 | 0x00 | 0x00 |        0 | clamped at start |
|   44 | 0x00 | 0x00 |        0 | clamped at start |
|   45 | 0x00 | 0x00 |        0 | clamped at start |
|   46 | 0x00 | 0x00 |        0 | clamped at start |
|   47 | 0x00 | 0x00 |        0 | clamped at start |
|   48 | 0x00 | 0x00 |        0 | clamped at start |
|   49 | 0x00 | 0x00 |        0 | clamped at start |
|   50 | 0x00 | 0x00 |        0 | clamped at start |
|   51 | 0x00 | 0x00 |        0 | clamped at start |
|   52 | 0x00 | 0x00 |        0 | clamped at start |
|   53 | 0x00 | 0x00 |        0 | clamped at start |
|   54 | 0x00 | 0x00 |        0 | clamped at start |
|   55 | 0x00 | 0x00 |        0 | clamped at start |
|   56 | 0x00 | 0x00 |        0 | clamped at start |
|   57 | 0x00 | 0x00 |        0 | clamped at start |
|   58 | 0x00 | 0x00 |        0 | clamped at start |
|   59 | 0x00 | 0x00 |        0 | clamped at start |
|   60 | 0x00 | 0x00 |        0 | clamped at start |
|   61 | 0x00 | 0x00 |        0 | clamped at start |
|   62 | 0x00 | 0x00 |        0 | clamped at start |
|   63 | 0x00 | 0x00 |        0 | clamped at start |
|   64 | 0x00 | 0x00 |        0 | clamped at start |
|   65 | 0x00 | 0x00 |        0 | clamped at start |
|   66 | 0x00 | 0x00 |        0 | clamped at start |
|   67 | 0x00 | 0x00 |        0 | clamped at start |
|   68 | 0x00 | 0x00 |        0 | clamped at start |
|   69 | 0x00 | 0x00 |        0 | clamped at start |
|   70 | 0x00 | 0x00 |        0 | clamped at start |
|   71 | 0x00 | 0x00 |        0 | clamped at start |
|   72 | 0x00 | 0x00 |        0 | clamped at start |
|   73 | 0x00 | 0x00 |        0 | clamped at start |
|   74 | 0x00 | 0x00 |        0 | clamped at start |
|   75 | 0x00 | 0x00 |        0 | clamped at start |
|   76 | 0x00 | 0x00 |        0 | clamped at start |
|   77 | 0x00 | 0x00 |        0 | clamped at start |
|   78 | 0x00 | 0x00 |        0 | clamped at start |
|   79 | 0x00 | 0x00 |        0 | clamped at start |
|   80 | 0x00 | 0x00 |        0 | clamped at start |
|   81 | 0x00 | 0x00 |        0 | clamped at start |
|   82 | 0x00 | 0x00 |        0 | clamped at start |
|   83 | 0x05 | 0x00 |        5 | START THRESHOLD |
|   84 | 0x0E | 0x00 |       14 |  |
|   85 | 0x0E | 0x00 |       14 |  |
|   86 | 0x17 | 0x00 |       23 |  |
|   87 | 0x1D | 0x00 |       29 |  |
|   88 | 0x23 | 0x00 |       35 |  |
|   89 | 0x28 | 0x00 |       40 |  |
|   90 | 0x2E | 0x00 |       46 |  |
|   91 | 0x34 | 0x00 |       52 |  |
|   92 | 0x3F | 0x00 |       63 |  |
|   93 | 0x40 | 0x00 |       64 |  |
|   94 | 0x48 | 0x00 |       72 |  |
|   95 | 0x4C | 0x00 |       76 |  |
|   96 | 0x52 | 0x00 |       82 |  |
|   97 | 0x5A | 0x00 |       90 |  |
|   98 | 0x5E | 0x00 |       94 |  |
|   99 | 0x64 | 0x00 |      100 |  |
|  100 | 0x6C | 0x00 |      108 |  |
|  101 | 0x71 | 0x00 |      113 |  |
|  102 | 0x77 | 0x00 |      119 |  |
|  103 | 0x7B | 0x00 |      123 |  |
|  104 | 0x83 | 0x00 |      131 |  |
|  105 | 0x89 | 0x00 |      137 |  |
|  106 | 0x8F | 0x00 |      143 |  |
|  107 | 0x95 | 0x00 |      149 |  |
|  108 | 0x9A | 0x00 |      154 |  |
|  109 | 0xA1 | 0x00 |      161 |  |
|  110 | 0xA6 | 0x00 |      166 |  |
|  111 | 0xAD | 0x00 |      173 |  |
|  112 | 0xB3 | 0x00 |      179 |  |
|  113 | 0xB9 | 0x00 |      185 |  |
|  114 | 0xBF | 0x00 |      191 |  |
|  115 | 0xC5 | 0x00 |      197 |  |
|  116 | 0xCC | 0x00 |      204 |  |
|  117 | 0xD3 | 0x00 |      211 |  |
|  118 | 0xD6 | 0x00 |      214 |  |
|  119 | 0xDE | 0x00 |      222 |  |
|  120 | 0xE4 | 0x00 |      228 |  |
|  121 | 0xE8 | 0x00 |      232 |  |
|  122 | 0xF0 | 0x00 |      240 |  |
|  123 | 0xF6 | 0x00 |      246 |  |
|  124 | 0xFA | 0x00 |      250 |  |
|  125 | 0x04 | 0x01 |      260 |  |
|  126 | 0x08 | 0x01 |      264 |  |
|  127 | 0x0E | 0x01 |      270 |  |
|  128 | 0x14 | 0x01 |      276 |  |
|  129 | 0x1A | 0x01 |      282 |  |
|  130 | 0x20 | 0x01 |      288 |  |
|  131 | 0x25 | 0x01 |      293 |  |
|  132 | 0x2C | 0x01 |      300 |  |
|  133 | 0x33 | 0x01 |      307 |  |
|  134 | 0x3A | 0x01 |      314 |  |
|  135 | 0x3F | 0x01 |      319 |  |
|  136 | 0x45 | 0x01 |      325 |  |
|  137 | 0x4B | 0x01 |      331 |  |
|  138 | 0x51 | 0x01 |      337 |  |
|  139 | 0x57 | 0x01 |      343 |  |
|  140 | 0x5D | 0x01 |      349 |  |
|  141 | 0x63 | 0x01 |      355 |  |
|  142 | 0x69 | 0x01 |      361 |  |
|  143 | 0x6F | 0x01 |      367 |  |
|  144 | 0x74 | 0x01 |      372 |  |
|  145 | 0x7B | 0x01 |      379 |  |
|  146 | 0x80 | 0x01 |      384 |  |
|  147 | 0x89 | 0x01 |      393 |  |
|  148 | 0x8D | 0x01 |      397 |  |
|  149 | 0x94 | 0x01 |      404 |  |
|  150 | 0x9B | 0x01 |      411 |  |
|  151 | 0xA0 | 0x01 |      416 |  |
|  152 | 0xA6 | 0x01 |      422 |  |
|  153 | 0xAC | 0x01 |      428 |  |
|  154 | 0xB2 | 0x01 |      434 |  |
|  155 | 0xB8 | 0x01 |      440 |  |
|  156 | 0xBE | 0x01 |      446 |  |
|  157 | 0xC4 | 0x01 |      452 |  |
|  158 | 0xCA | 0x01 |      458 |  |
|  159 | 0xD0 | 0x01 |      464 |  |
|  160 | 0xD5 | 0x01 |      469 |  |
|  161 | 0xDE | 0x01 |      478 |  |
|  162 | 0xE4 | 0x01 |      484 |  |
|  163 | 0xE7 | 0x01 |      487 |  |
|  164 | 0xED | 0x01 |      493 |  |
|  165 | 0xF6 | 0x01 |      502 |  |
|  166 | 0xF9 | 0x01 |      505 |  |
|  167 | 0x02 | 0x02 |      514 |  |
|  168 | 0x08 | 0x02 |      520 |  |
|  169 | 0x0D | 0x02 |      525 |  |
|  170 | 0x13 | 0x02 |      531 |  |
|  171 | 0x19 | 0x02 |      537 |  |
|  172 | 0x1D | 0x02 |      541 |  |
|  173 | 0x25 | 0x02 |      549 |  |
|  174 | 0x2B | 0x02 |      555 |  |
|  175 | 0x31 | 0x02 |      561 |  |
|  176 | 0x37 | 0x02 |      567 |  |
|  177 | 0x3F | 0x02 |      575 |  |
|  178 | 0x43 | 0x02 |      579 |  |
|  179 | 0x49 | 0x02 |      585 |  |
|  180 | 0x51 | 0x02 |      593 |  |
|  181 | 0x54 | 0x02 |      596 |  |
|  182 | 0x5A | 0x02 |      602 |  |
|  183 | 0x63 | 0x02 |      611 |  |
|  184 | 0x68 | 0x02 |      616 |  |
|  185 | 0x6F | 0x02 |      623 |  |
|  186 | 0x74 | 0x02 |      628 |  |
|  187 | 0x7A | 0x02 |      634 |  |
|  188 | 0x80 | 0x02 |      640 |  |
|  189 | 0x86 | 0x02 |      646 |  |
|  190 | 0x8C | 0x02 |      652 |  |
|  191 | 0x91 | 0x02 |      657 |  |
|  192 | 0x98 | 0x02 |      664 |  |
|  193 | 0x9E | 0x02 |      670 |  |
|  194 | 0xA6 | 0x02 |      678 |  |
|  195 | 0xAA | 0x02 |      682 |  |
|  196 | 0xB0 | 0x02 |      688 |  |
|  197 | 0xB8 | 0x02 |      696 |  |
|  198 | 0xBC | 0x02 |      700 |  |
|  199 | 0xC4 | 0x02 |      708 |  |
|  200 | 0xC9 | 0x02 |      713 |  |
|  201 | 0xCF | 0x02 |      719 |  |
|  202 | 0xD5 | 0x02 |      725 |  |
|  203 | 0xDB | 0x02 |      731 |  |
|  204 | 0xE2 | 0x02 |      738 |  |
|  205 | 0xE5 | 0x02 |      741 |  |
|  206 | 0xEE | 0x02 |      750 |  |
|  207 | 0xF3 | 0x02 |      755 |  |
|  208 | 0xF8 | 0x02 |      760 |  |
|  209 | 0xFF | 0x02 |      767 |  |
|  210 | 0x05 | 0x03 |      773 |  |
|  211 | 0x0A | 0x03 |      778 |  |
|  212 | 0x11 | 0x03 |      785 |  |
|  213 | 0x17 | 0x03 |      791 |  |
|  214 | 0x1D | 0x03 |      797 |  |
|  215 | 0x24 | 0x03 |      804 |  |
|  216 | 0x2A | 0x03 |      810 |  |
|  217 | 0x30 | 0x03 |      816 |  |
|  218 | 0x36 | 0x03 |      822 |  |
|  219 | 0x3D | 0x03 |      829 |  |
|  220 | 0x42 | 0x03 |      834 |  |
|  221 | 0x46 | 0x03 |      838 |  |
|  222 | 0x4E | 0x03 |      846 |  |
|  223 | 0x52 | 0x03 |      850 |  |
|  224 | 0x59 | 0x03 |      857 |  |
|  225 | 0x62 | 0x03 |      866 |  |
|  226 | 0x66 | 0x03 |      870 |  |
|  227 | 0x6C | 0x03 |      876 |  |
|  228 | 0x74 | 0x03 |      884 |  |
|  229 | 0x78 | 0x03 |      888 |  |
|  230 | 0x7E | 0x03 |      894 |  |
|  231 | 0x84 | 0x03 |      900 |  |
|  232 | 0x8B | 0x03 |      907 |  |
|  233 | 0x92 | 0x03 |      914 |  |
|  234 | 0x97 | 0x03 |      919 |  |
|  235 | 0x9D | 0x03 |      925 |  |
|  236 | 0xA3 | 0x03 |      931 |  |
|  237 | 0xA9 | 0x03 |      937 |  |
|  238 | 0xB2 | 0x03 |      946 |  |
|  239 | 0xB5 | 0x03 |      949 |  |
|  240 | 0xBB | 0x03 |      955 |  |
|  241 | 0xC3 | 0x03 |      963 |  |
|  242 | 0xC7 | 0x03 |      967 |  |
|  243 | 0xCD | 0x03 |      973 |  |
|  244 | 0xD3 | 0x03 |      979 |  |
|  245 | 0xD9 | 0x03 |      985 |  |
|  246 | 0xDF | 0x03 |      991 |  |
|  247 | 0xE5 | 0x03 |      997 | STOP THRESHOLD |
|  248 | 0xE5 | 0x03 |      997 | clamped at stop |
|  249 | 0xE5 | 0x03 |      997 | clamped at stop |
|  250 | 0xE5 | 0x03 |      997 | clamped at stop |
|  251 | 0xE5 | 0x03 |      997 | clamped at stop |
|  252 | 0xE5 | 0x03 |      997 | clamped at stop |
|  253 | 0xE5 | 0x03 |      997 | clamped at stop |
|  254 | 0xE5 | 0x03 |      997 | clamped at stop |
|  255 | 0xE5 | 0x03 |      997 | clamped at stop |

## Key Findings
- Idle broadcast uses **little-endian** byte order in bytes[2:3] (opposite of commanded mode)
- Start threshold: 0x23=83 (position starts reporting > 0)
- Stop threshold: 0x23=247 (position clamps at 997)
- Usable range: 0x23 83-247 = 164 steps -> 0-997 position
- Scale: ~6.1 position counts per 0x23 step
