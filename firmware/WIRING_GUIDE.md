# MechMind AI — ESP32 Hardware Wiring Guide 🛠️🔌

**Reference Board:** ESP32-WROOM-32D (38-Pin Layout, USB at the bottom)
**Microcontroller:** ESP32 DevKit (Pins 1 to 19 on Left, Pins 20 to 38 on Right)
**Date:** 19 September 2026

---

## 🧭 Jumper Wire Identification Guide (Know Your Wires!)

Before connecting anything, identify which jumper wire types you have in your ribbon:

| Wire Type Name                      |   Abbreviation   | End 1 Looks Like                  | End 2 Looks Like                     | How It Is Used in This Project                                                                |
| ----------------------------------- | :---------------: | --------------------------------- | ------------------------------------ | --------------------------------------------------------------------------------------------- |
| **Male-to-Male**              |   **M-M**   | Pointed metal pin (stiff pin)     | Pointed metal pin (stiff pin)        | **Main jumpers:** Plugs from breadboard hole to breadboard hole or ESP32 pin.           |
| **Male-to-Female**            |   **M-F**   | Pointed metal pin (stiff pin)     | Plastic collar with hole (socket)    | **Probe extension:** Male pin into breadboard, Female socket grips sensor leads.        |
| **Female-to-Female**          |   **F-F**   | Plastic collar with hole (socket) | Plastic collar with hole (socket)    | Not used for breadboards (used for boards with tall pin headers).                             |
| **Cut Jumper (Male-to-Bare)** | **Cut M-M** | Pointed metal pin (stiff pin)     | Bare exposed stripped copper strands | **Charger Board:** Bare copper taped to flat PCB pad, Male pin into ESP32 / breadboard. |

> 💡 **Visual Rule:**
>
> * **"Male"** = Stiff pointed needle/pin sticking OUT.
> * **"Female"** = Plastic block with a hole going IN (a receptacle/socket).
> * **"Bare Copper"** = Stripped metal wires with no pin.

---

## 🗺️ Pin Number Quick-Reference (Matching Your Picture!)

Look at your ESP32 with the Micro-USB port facing **DOWN**:

* **Left Side (Pins 1 to 19):**

  * **Pin 1 (Top Left):** `3.3V` ⬅️ **Main 3.3V Power Out**
  * **Pin 8 (8th from Top):** `GIOP33` ⬅️ Diagnostic Power Probe
  * **Pin 14 (14th from Top):** `GND` ⬅️ Ground
  * **Pin 19 (Bottom Left):** `Vin 5V` ⬅️ **Battery 5V Power Input**
* **Right Side (Pins 38 down to 20):**

  * **Pin 38 (Top Right):** `GND` ⬅️ **Main Ground Rail**
  * **Pin 36 (3rd from Top):** `GIOP22` ⬅️ **I2C SCL (Clock for ADXL345)**
  * **Pin 33 (6th from Top):** `GIOP21` ⬅️ **I2C SDA (Data for ADXL345)**
  * **Pin 26 (13th from Top / 7th from Bottom):** `GIOP4` ⬅️ **Temperature Data for DS18B20**
  * **Pin 25 (9th from Top):** `GIOP25` ⬅️ **I2S WS (Word Select for INMP441)**
  * **Pin 24 (10th from Top):** `GIOP33` ⬅️ **I2S SCK / BCLK (Serial Clock for INMP441)**
  * **Pin 23 (11th from Top):** `GIOP32` ⬅️ **I2S SD (Serial Data from INMP441)**

---

## 🔌 Exact Wire-by-Wire Connections

---

### PART 1: Powering the Rails (2 Wires)

#### 🔴 Wire 1: 3.3V Power

* **Jumper Wire Type:** **Male-to-Male (M-M)**
* **Wire Color:** Red
* **From:** Breadboard hole directly in line with **Pin 1 (Top Left pin, labeled `3.3V`)**
* **To:** Any hole in the **Red Rail (+)** along the edge of the breadboard.
* *(Powers the entire Red strip with 3.3V for your sensors).*

#### ⚫ Wire 2: Ground (GND)

* **Jumper Wire Type:** **Male-to-Male (M-M)**
* **Wire Color:** Black
* **From:** Breadboard hole directly in line with **Pin 38 (Top Right pin, labeled `GND`)**
* **To:** Any hole in the **Blue Rail (-)** along the edge of the breadboard.
* *(Connects the entire Blue strip to Ground).*

---

### PART 2: GY-291 ADXL345 Vibration Sensor (6 Wires — ALL Male-to-Male)

*Push the ADXL345 sensor's 8 pins into empty rows below the ESP32 on the breadboard.*

* 🔴 **Wire 3 — Male-to-Male (M-M, Red):**
  * **From:** Hole next to ADXL345 **`VCC`** ➡️ **To:** Any hole in the **Red Rail (+)**.
* 🔴 **Wire 4 — Male-to-Male (M-M, Red):**
  * **From:** Hole next to ADXL345 **`CS`** ➡️ **To:** Any hole in the **Red Rail (+)** *(Enables I2C mode)*.
* ⚫ **Wire 5 — Male-to-Male (M-M, Black):**
  * **From:** Hole next to ADXL345 **`GND`** ➡️ **To:** Any hole in the **Blue Rail (-)**.
* ⚫ **Wire 6 — Male-to-Male (M-M, Black):**
  * **From:** Hole next to ADXL345 **`SDO`** ➡️ **To:** Any hole in the **Blue Rail (-)** *(Sets I2C address 0x53)*.
* 🔵 **Wire 7 — Male-to-Male (M-M, Blue):**
  * **From:** Hole next to ADXL345 **`SDA`** ➡️ **To:** Breadboard hole directly in line with **Pin 33 (`GIOP21`)** *(6th pin down on the right side of ESP32)*.
* 🟡 **Wire 8 — Male-to-Male (M-M, Yellow):**
  * **From:** Hole next to ADXL345 **`SCL`** ➡️ **To:** Breadboard hole directly in line with **Pin 36 (`GIOP22`)** *(3rd pin down on the right side of ESP32)*.

*(Leave ADXL345 pins `INT1` and `INT2` empty).*

---

### PART 3: Waterproof DS18B20 Temperature Probe (Probe Leads + 1 Resistor + 1 Jumper Wire)

#### Direct Connections:

* 🔴 **Probe Red Lead (Power):** Push into any hole in the **Red Rail (+)**.
* ⚫ **Probe Black Lead (GND):** Push into any hole in the **Blue Rail (-)**.
* 🟡 **Probe Yellow Lead (Data):** Push into an empty row below the sensors (e.g. **Row 30**).
* 🟢 **Wire 9 — Male-to-Male (M-M, Green):**
  * **From:** **Row 30** (where Yellow probe lead sits) ➡️ **To:** Breadboard hole directly in line with **Pin 26 (`GIOP4`)** *(13th pin down on the right side of ESP32)*.
* 🪢 **4.7kΩ Resistor (Stripes: Yellow-Violet-Red-Gold):**
  * Push **Leg 1** into **Row 30** (where Yellow wire & Wire 9 are).
  * Push **Leg 2** into any hole in the **Red Rail (+)**.

---

#### 🧰 Pro-Tip: Stop Temperature Sensor Wires from Slipping Out of the Breadboard! ⚓

**Why it slips out:**
The DS18B20 probe has a **heavy black cable** and very **thin, soft stranded copper wires**. Breadboard spring clips only grip **stiff solid pins** tightly. When the probe moves, the soft wires easily pop out.

Here are the **3 best ways** to fix it:

##### 🌟 Method 1: The Female-to-Male (M-F) Extension Trick (Most Reliable!)

If you have **Male-to-Female (M-F)** jumper wires in your kit:

1. Take **3 Male-to-Female (M-F)** jumper wires (Red, Black, Yellow).
2. Plug the stiff **Male pins** firmly into the breadboard:
   * Red Male pin ➡️ **Red Rail (+)**
   * Black Male pin ➡️ **Blue Rail (-)**
   * Yellow Male pin ➡️ **Row 30**
3. Push each soft probe wire directly into the matching **Female socket** on the other end.
4. Wrap a small piece of **paper tape** around each joint. The stiff male pins will **never** fall out of the breadboard!

##### 🛠️ Method 2: The Stiff Resistor Leg Wrap (If using Male-to-Male wires)

1. Cut a small piece of a stiff component lead or spare resistor wire.
2. Twist the bare stranded copper of the probe wire tightly around the stiff metal lead.
3. Wrap paper tape around the joint, leaving ~1 cm of the stiff metal tip exposed.
4. Push the stiff metal tip into the breadboard hole — it grips with maximum force!

##### ⚓ Method 3: Cable Strain-Relief Anchor (Always Do This!)

* Tape the thick black probe cable **firmly to your table or the side of the breadboard** using paper tape about 5 cm before it reaches the breadboard.
* Any accidental tug or bump will pull on the tape, not the fragile wires!

---

---

### PART 4: 18650 Battery Holder & Charger Module (Field Power Setup) 🔋⚡

> ⚠️ **CRITICAL SAFETY RULES BEFORE YOU CONNECT:**
>
> 1. **NEVER plug BOTH your laptop USB cable AND the battery 5V into the ESP32 simultaneously.** When powering from battery, **unplug the Micro-USB cable from your laptop first**!
> 2. **BATTERY POLARITY MATTERS:** In any standard 18650 battery holder, the **SPRING terminal is always NEGATIVE (-)**. The flat metal plate is always **POSITIVE (+)**. Never insert the 18650 backwards!

---

#### 🧰 Step 1: Understand Your 18650 Battery Holder Wires

Your 18650 battery holder comes with two pre-soldered flexible wires:

* 🔴 **Red Wire:** Positive (`+`) terminal (comes from the flat metal contact end).
* ⚫ **Black Wire:** Negative (`-`) terminal (comes from the **spring** contact end).

*(Keep the 18650 battery OUT of the holder while wiring to avoid short circuits!)*

---

#### 🔌 Step 2: Connecting the Battery Holder to Your Charger Module

*(Matching your exact board: IP5306 Type-C 5V 2A Boost & Charger PCB with "100" inductor)*

This board has **flat surface-mount silver solder pads** along the PCB edges with NO pin headers and NO through-holes.

The 4 pads are:

* **`B+` (or `BAT+`):** 3.7V Battery Positive terminal.
* **`B-` (or `BAT-`):** 3.7V Battery Negative terminal.
* **`OUT+` (or `5V` / `V+`):** Boosted 5V power output to ESP32.
* **`OUT-` (or `GND` / `V-`):** Ground return to breadboard.

---

#### ✂️ Exactly Which Jumper Wires to Use & How to Make Wire 10 & Wire 11:

Because the charger board has flat metal pads (no holes to push pins into), you prepare **two custom wires** using standard jumper wires:

1. **Pick the Wires from Your Ribbon:**

   * Take **1 RED Male-to-Male (M-M)** jumper wire *(or Red Male-to-Female)*.
   * Take **1 BLACK Male-to-Male (M-M)** jumper wire *(or Black Male-to-Female)*.
2. **Cut and Strip ONE END ONLY (Create Male-to-Bare-Copper Wires):**

   * Take scissors or nail clippers.
   * **Red Wire:** Cut the metal pin off **ONE END ONLY**. Leave the pointed Male pin on the other end untouched!
   * **Black Wire:** Cut the metal pin off **ONE END ONLY**. Leave the pointed Male pin on the other end untouched!
   * Strip about **6mm to 8mm** of plastic insulation from the cut ends to expose the shiny copper strands.
   * Twist the copper strands tightly with your fingertips so they form a neat, flat bundle.
3. **Attach to the Charger Board Pads (Using Paper Tape or Solder):**

   * Lay the bare copper of the **Red wire** flat across the silver **`OUT+`** (or `5V`) pad.
   * Press down and wrap 2–3 tight loops of **paper tape** around the board to clamp the copper flat against the pad.
   * Lay the bare copper of the **Black wire** flat across the silver **`OUT-`** (or `GND`) pad.
   * Wrap with paper tape to clamp it securely.
   * *(⚠️ Safety Check: Make sure the bare copper of the Red and Black wires do NOT touch each other!)*
4. **Plug the Male Pins into ESP32 & Breadboard:**

   * 🔴 **Wire 10 (Red Cut M-M Wire):**
     * **Bare copper end:** Taped/soldered to **`OUT+`** (5V) pad on module.
     * **Male pin end:** Plugs into **Pin 19 (`Vin 5V`)** on the ESP32 *(very bottom pin on the LEFT side, Row 19, Column `a` or `b`, right next to the USB port)*.
   * ⚫ **Wire 11 (Black Cut M-M Wire):**
     * **Bare copper end:** Taped/soldered to **`OUT-`** (GND) pad on module.
     * **Male pin end:** Plugs into any hole in the **Blue Rail (-)** on your breadboard.

---

#### 🎯 Step-by-Step Action Checklist:

* [X] **Step 1 (DONE!):** Battery holder Red wire connected to **`B+`** and Black wire connected to **`B-`**.
* [X] **Step 2 (NEXT):** Cut ONE end off 1 Red and 1 Black Male-to-Male jumper wire, strip 8mm copper, and tape/solder Red bare end to **`OUT+`** and Black bare end to **`OUT-`**.
* [X] **Step 3:** Push the Red wire Male pin into **Pin 19 (`Vin 5V`)** and Black wire Male pin into the **Blue Rail (-)**.
* [X] **Step 4 (CRITICAL SAFETY):** **Unplug the laptop USB cable from the ESP32.**
* [ ] **Step 5:** Insert the 18650 battery into your blue holder:
  * **Flat negative base (-)** pushes against the **SPRING** at the top!
  * **Raised button top (+)** rests against the flat plate at the bottom.
* [ ] **Step 6:** Watch the ESP32 power LED light up — you are now 100% wireless!

---

#### 🔋 Step 3: Recharging the Battery & Pass-Through Charging

* **Can you charge while the ESP32 is running? YES!**
  * Your charger/boost module features **pass-through power**: you can plug a standard 5V USB-C charger into the **charging module's Type-C port** while the ESP32 is actively streaming telemetry!
  * The module will charge the 18650 cell while simultaneously boosting 5V out of `OUT+` to power your ESP32.
  * ⚠️ **SAFETY DIRECTIVE:** Always plug the charger into the **charger module's Type-C port**. NEVER plug a second USB cable into the ESP32's micro-USB port while Wire 10 is connected to `Vin 5V`.

* **Status LEDs on the board:**
  * 🔴 **Red LED Blinking/On:** Battery is actively charging.
  * 🔵 **Blue/Green LED Solid:** Battery is fully charged to 4.2V.

---

### 🔘 How to Turn Off Power Without Removing the Battery Every Time

You do not need to pull the 18650 cell out of the blue holder every time you want to shut down your system.

#### ❓ Can I use the 4-pin button from my kit?
* The 4-pin button in your electronics kit is a **momentary tactile pushbutton** (normally open).
* It only makes contact **while your finger is pressing it down**. As soon as you let go, it disconnects. Because of this, it cannot hold the main 5V power line open/closed permanently on its own without latching circuitry.

#### 💡 The 3 Best Solutions:

1. **Option 1: The Quick Jumper Disconnect (Easiest — 0 extra parts needed!):**
   * Simply pull **Wire 10 (Red Male Pin)** out of **Pin 19 (`Vin 5V`)** on your ESP32!
   * Leaving Wire 10 unplugged cuts 100% of current to the ESP32. The battery stays safely in the holder with zero power drain.
   * To power it back on, just push Wire 10 back into Pin 19 (`Vin 5V`).

2. **Option 2: Using the Charger Module's Sleep / Key Mode (If your board has IP5306):**
   * Check if your charger module has a tiny built-in SMD button or a solder pad labeled **`KEY`** or **`K`**:
     * **Double-click:** Shuts down the 5V boost converter output (`OUT+` drops to 0V, ESP32 sleeps, battery draw <50µA).
     * **Single-click:** Wakes up the 5V output and boots the ESP32!
   * *If your board has a `KEY` pin/pad:* You can solder your 4-pin momentary pushbutton between **`KEY`** and **`GND`** to turn the power on and off with single and double presses!

3. **Option 3: An SPST Slide Switch or Rocker Switch (Permanent On/Off):**
   * Use a 2-pin or 3-pin latching slide switch (stays in position when moved).
   * Splice it in series along **Wire 10 (the Red 5V line)** between `OUT+` and `Pin 19 (Vin 5V)`.
   * Sliding it to `OFF` physically breaks the power circuit.

---

### PART 5: INMP441 I2S MEMS Microphone (Sound Sensor — 5 Wires + 1 Ground Tie)

> 🎤 **What is the INMP441?**
>
> It's a tiny digital microphone that outputs audio data over the I2S protocol (a digital audio bus). Unlike analog microphones, it sends clean digital samples directly to the ESP32 — no ADC needed. The ESP32 reads raw PCM audio, calculates the RMS (root-mean-square) amplitude, and converts it to a decibel (dB SPL) reading for acoustic anomaly detection.

---

#### 🔍 Step 1: Identify Your INMP441 Board (Circular HW-906CD Model)

Your sensor is the **circular `HW-906CD` INMP441 MEMS microphone module** (a round coin-sized black PCB).

Looking directly at the front of the board (with `HW-906CD` printed in the middle):

```
             ╭────────────────╮
             │    HW-906CD    │
     (SD)  ○ │       ○        │ ○  (SCK)
    (VDD)  ○ │   (Mic Hole)   │ ○  (WS)
    (GND)  ○ │                │ ○  (L/R)
             ╰────────────────╯
              LEFT         RIGHT
```

##### 📋 Exact Pin Assignment on the HW-906CD:

| Side of HW-906CD | Pin Label | Full Name | Where It Connects on ESP32 | Purpose |
|---|---|---|---|---|
| **Left** | **`SD`** | Serial Data | **Pin 7 (`GPIO32`)** *(7th pin down, **LEFT** side of ESP32)* | Digital audio data line read by ESP32 |
| **Left** | **`VDD`** | 3.3V Power | **Red Rail (+)** | 3.3V power supply (**Never connect to 5V!**) |
| **Left** | **`GND`** | Ground | **Blue Rail (-)** | Common ground |
| **Right** | **`SCK`** | Serial Clock | **Pin 31 (`GPIO19`)** *(8th pin down, **RIGHT** side of ESP32)* | I2S bit clock (BCLK) |
| **Right** | **`WS`** | Word Select | **Pin 9 (`GPIO25`)** *(9th pin down, **LEFT** side of ESP32)* | I2S word select clock (LRCLK) |
| **Right** | **`L/R`** | Left/Right Select | **Blue Rail (-)** | Connect to **GND** for Left channel (Required!) |

> ⚠️ **Important:** The `L/R` pin MUST be tied to **GND** (Blue Rail). If left ungrounded/floating, the microphone will not output any audio frames!

---

#### 🔌 Step 2: How to Connect the Circular HW-906CD to Your Breadboard

##### ⚠️ Why You Cannot Push This Board Flat Into the Breadboard
On a solderless breadboard, **holes `a, b, c, d, e` in the same horizontal row are connected together underneath**.
Because the HW-906CD is a round board with 3 pins on the left and 3 on the right:
* If you tried to push it into the breadboard, pins on the left and right in the same rows would be **short-circuited together**.
* **Do NOT attempt to push the round PCB directly into the breadboard clips.**

---

##### 🛠️ How to Connect the Pins (Choose Method A or B):

###### Method A: Solder Header Pins + Female-to-Male (F-M) Wires (Recommended)
1. Take a strip of standard male header pins (often included with sensor kits).
2. Solder 3 pins on the left (`SD`, `VDD`, `GND`) and 3 pins on the right (`SCK`, `WS`, `L/R`), pointing downward or upward.
3. Use **6 Female-to-Male (F-M) Dupont jumper wires**:
   * Push the **Female ends** directly onto the 6 soldered pins on the HW-906CD.
   * Plug the **Male ends** into the Breadboard rails and ESP32 GPIO positions.

```
       HW-906CD Module (Free-floating / Raised)
        ┌───────────────────────────────────┐
        │  [SD]   [VDD]   [GND]             │  (Left pins)
        │  [SCK]  [WS]    [L/R]             │  (Right pins)
        └───────────────────────────────────┘
             │      │       │
      (6x Female-to-Male Dupont Jumper Wires)
             │      │       │
             ▼      ▼       ▼
       [Breadboard Rails & ESP32 GPIO Holes]
```

###### Method B: Direct Wire Soldering (Permanent & Compact)
* Cut 6 jumper wires, strip a tiny piece of insulation off one end, insert through the 6 holes on the HW-906CD, and solder directly.
* The male ends of the wires then plug directly into your breadboard!

###### Method C: Quick Testing (If you don't have a soldering iron right now)
* Insert male jumper wire pins through each hole and bend slightly or use header pins pushed through with a tiny bit of tape/putty for temporary contact testing before final soldering.

##### 🎤 Microphone Orientation
Make sure the **tiny silver acoustic hole** in the center faces outward toward the room/machinery so it can freely capture acoustic frequencies. Do not block or cover the hole with glue or tape.

---

#### 🔌 Step 3: Wire-by-Wire Connections (5 Wires + 1 Ground Tie)

> 💡 **Jumper Wire Note:** If your INMP441 module is plugged into column `a`, use **Male-to-Male (M-M)** wires from column `b`. If your module has pins in a circle/2x3 and you are connecting directly to its pins, use **Female-to-Male (F-M)** wires (Female end on module pin, Male end into destination).

* 🔴 **Wire 12 — Red (M-M or F-M):**
  * **From:** INMP441 **`VDD`** (or column `b` in VDD row) ➡️ **To:** Any hole in the **Red Rail (+)**.
  * *(Powers the microphone with 3.3V.)*

* ⚫ **Wire 13 — Black (M-M or F-M):**
  * **From:** INMP441 **`GND`** (or column `b` in GND row) ➡️ **To:** Any hole in the **Blue Rail (-)**.
  * *(Common ground.)*

* ⚫ **Wire 14 — Black (M-M or F-M):**
  * **From:** INMP441 **`L/R`** (or column `b` in L/R row) ➡️ **To:** Any hole in the **Blue Rail (-)**.
  * *(Ties L/R to GND = Left channel. This is required — do not skip!)*

* 🟠 **Wire 15 — Orange / Any color (M-M or F-M):**
  * **From:** INMP441 **`WS`** (Right side of HW-906CD) ➡️ **To:** Breadboard hole directly in line with **Pin 9 (`GPIO25`)** *(9th pin down on the **LEFT** side of ESP32 — column `a`, `b`, `c`, or `d` in row 9)*.
  * *(Word Select / LRCLK signal.)*

* 🟣 **Wire 16 — Purple / Any color (M-M or F-M):**
  * **From:** INMP441 **`SCK`** (Right side of HW-906CD) ➡️ **To:** Breadboard hole directly in line with **Pin 31 (`GPIO19`)** *(8th pin down on the **RIGHT** side of ESP32 — column `g`, `h`, `i`, or `j` in row for Pin 31)*.
  * *(Serial Clock / BCLK signal.)*

* 🟤 **Wire 17 — Brown / Any color (M-M or F-M):**
  * **From:** INMP441 **`SD`** (Left side of HW-906CD) ➡️ **To:** Breadboard hole directly in line with **Pin 7 (`GPIO32`)** *(7th pin down on the **LEFT** side of ESP32 — column `a`, `b`, `c`, or `d` in row 7)*.
  * *(Serial Data — the actual digital audio stream read by ESP32.)*

---

#### 🧪 Quick Verification After Wiring:

1. Double-check that **`L/R`** is tied to **GND** (Blue Rail) — not left floating!
2. Make sure **`VDD`** goes to the **Red Rail (+)** (3.3V), NOT to 5V. The INMP441 is a 3.3V device.
3. Confirm no wires from the INMP441 touch the ADXL345 or DS18B20 rows.
4. The tiny **silver microphone hole** on the board should face upward / outward, not pressed against the breadboard.

---

#### 🔧 Enable in Firmware:

In [`mechmind_node.ino`](file:///c:/Users/XPS/Downloads/china/mechmind-ai/firmware/mechmind_node/mechmind_node.ino) lines 51-61:

```cpp
#define I2S_WS_PIN     25  // Pin 9 (Left: GPIO25)
#define I2S_SCK_PIN    19  // Pin 31 (Right: GPIO19) - Plenty of room!
#define I2S_SD_PIN     32  // Pin 7 (Left: GPIO32)
#define ENABLE_I2S_MIC true
```

Upload the firmware via USB. The serial monitor should now show real `sound_db` readings instead of the simulated baseline.

---

## 📊 Complete Wiring & Jumper Wire Specification Table

|         Wire / Item         |         Jumper Wire Type         |   Color   | From (Origin)                                 | To (Destination)                                     | Purpose                     |
| :-------------------------: | :------------------------------: | :-------: | --------------------------------------------- | ---------------------------------------------------- | --------------------------- |
|      **Wire 1**      |   **Male-to-Male (M-M)**   |  🔴 Red  | **Pin 1** (Top Left: `3.3V`)          | **Red Rail (+)**                               | 3.3V Sensor Power Rail      |
|      **Wire 2**      |   **Male-to-Male (M-M)**   | ⚫ Black | **Pin 38** (Top Right: `GND`)         | **Blue Rail (-)**                              | Common Ground Rail          |
|      **Wire 3**      |   **Male-to-Male (M-M)**   |  🔴 Red  | ADXL345`VCC`                                | **Red Rail (+)**                               | Accelerometer 3.3V Power    |
|      **Wire 4**      |   **Male-to-Male (M-M)**   |  🔴 Red  | ADXL345`CS`                                 | **Red Rail (+)**                               | Enables I2C mode            |
|      **Wire 5**      |   **Male-to-Male (M-M)**   | ⚫ Black | ADXL345`GND`                                | **Blue Rail (-)**                              | Accelerometer Ground        |
|      **Wire 6**      |   **Male-to-Male (M-M)**   | ⚫ Black | ADXL345`SDO`                                | **Blue Rail (-)**                              | Sets I2C address to`0x53` |
|      **Wire 7**      |   **Male-to-Male (M-M)**   |  🔵 Blue  | ADXL345`SDA`                                | **Pin 33** (6th down, Right: `GPIO21`)       | I2C Data Line               |
|      **Wire 8**      |   **Male-to-Male (M-M)**   | 🟡 Yellow | ADXL345`SCL`                                | **Pin 36** (3rd down, Right: `GPIO22`)       | I2C Clock Line              |
|      **Wire 9**      |   **Male-to-Male (M-M)**   | 🟢 Green | Row 30 (Yellow probe lead)                    | **Pin 26** (13th down, Right: `GPIO4`)        | Temperature Data Line       |
|     **Resistor**     |    **4.7kΩ Resistor**    |   Multi   | Row 30 (Yellow probe lead)                    | **Red Rail (+)**                               | OneWire Pull-up Resistor    |
|  **Holder Red Lead**  |   **Pre-attached Lead**   |  🔴 Red  | 18650 Holder Flat Plate (+)                   | Charger Board**`B+`**                        | Battery Positive Input      |
| **Holder Black Lead** |   **Pre-attached Lead**   | ⚫ Black | 18650 Holder Spring (-)                       | Charger Board**`B-`**                        | Battery Negative Input      |
|      **Wire 10**      | **Cut M-M (Male-to-Bare)** |  🔴 Red  | Charger Board**`OUT+`** (Bare copper) | **Pin 19** (Bottom Left: `Vin 5V`, Male Pin) | 5V Boosted Power to ESP32   |
|      **Wire 11**      | **Cut M-M (Male-to-Bare)** | ⚫ Black | Charger Board**`OUT-`** (Bare copper) | **Blue Rail (-)** (Male Pin)                   | Battery Ground Return       |
|      **Wire 12**      | **M-M or F-M**             |  🔴 Red  | INMP441`VDD`                                | **Red Rail (+)**                               | Microphone 3.3V Power       |
|      **Wire 13**      | **M-M or F-M**             | ⚫ Black | INMP441`GND`                                | **Blue Rail (-)**                              | Microphone Ground           |
|      **Wire 14**      | **M-M or F-M**             | ⚫ Black | INMP441`L/R`                                | **Blue Rail (-)**                              | Left Channel Select (GND)   |
|      **Wire 15**      | **M-M or F-M**             | 🟠 Orange | INMP441`WS`                                 | **Pin 9** (9th down, Left: `GPIO25`)         | I2S Word Select (LRCLK)     |
|      **Wire 16**      | **M-M or F-M**             | 🟣 Purple | INMP441`SCK`                                | **Pin 31** (8th down, Right: `GPIO19`)       | I2S Serial Clock (BCLK)     |
|      **Wire 17**      | **M-M or F-M**             | 🟤 Brown | INMP441`SD`                                 | **Pin 7** (7th down, Left: `GPIO32`)         | I2S Serial Data (Audio In)  |

---

### ✅ Pre-Flight Checklist Before Inserting Battery:

1. [ ] **Unplug the laptop USB cable from the ESP32.**
2. [ ] Double-check that the **Holder Black wire** is connected to **`B-`** and **Holder Red wire** to **`B+`**.
3. [ ] Double-check that **Wire 10 (Red)** connects `OUT+` to **Pin 19 (`Vin 5V`)**.
4. [ ] Double-check that **Wire 11 (Black)** connects `OUT-` to **Blue Rail (-)**.
5. [ ] Insert the 18650 cell into the holder: **Flat negative base pushed against the SPRING**, raised button top against the flat metal plate.
6. [ ] Confirm the ESP32 red power LED turns on!
