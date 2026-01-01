# 🖥️ DCS Monitor Tool

**Create the Perfect MonitorSetup Layout.lua for your DCS Configuration**

> Created by **lxnx382**

A visual tool for configuring multi-monitor setups in DCS World. The tool reads your Windows monitor layout, lets you assign each monitor as viewport or panel, and exports the configuration for DCS!

---

## ✨ Features

- 🎯 **Visual Monitor Layout** - See your actual Windows monitor arrangement in real-time
- 🖱️ **Easy Assignment** - Assign monitors as viewports or cockpit panels with dropdown menus
- 📐 **1:1 Physical Mapping** - Uses your exact monitor positions and resolutions
- � **Per-Monitor Offsets** - Fine-tune X/Y position and override width/height for each monitor
- 💾 **Save & Load Layouts** - Save your complete setup as .dml files and restore them anytime
- 🔄 **Persistent Configuration** - Remembers your assignments when refreshing monitors
- 🎨 **Interactive Canvas** - Zoom (Ctrl+Scroll) and pan (Middle Mouse) for perfect positioning
- 📊 **DCS Coordinate Preview** - Shows both Windows and DCS coordinates on each monitor
- 🎯 **Bounding Box Display** - Orange box shows your total DCS render area and resolution
- 💾 **Quick Save** - Export directly to your DCS MonitorSetup folder (saves .lua + .dml)
- 📝 **Lua Preview** - Review generated code before saving

---

## 🚀 Quick Start

### Prerequisites

```bash
pip install PySide6 screeninfo
```

### Running the Tool

```bash
python dcs_monitor_tool.py
```

---

## 📖 How to Use

### 1️⃣ **Arrange Monitors in Windows**
First, arrange your physical monitors in Windows Display Settings to match your desk setup. The tool will read this exact layout.

### 2️⃣ **Load Monitor Layout**
When you launch the tool, it automatically detects all your Windows monitors and displays them in their exact positions. If you change your Windows monitor arrangement, click **"🔄 Refresh Monitor Layout"** to reload.

### 3️⃣ **Configure Your Layout**
- **Layout Name**: Enter a name for your setup (e.g., "F18_Cockpit")
- **Description**: Add a description (optional)

### 4️⃣ **Assign Monitors**
Click the dropdown on each monitor to assign it as:
- **Viewports**: `Left`, `Center`, `Right` (main 3D views)
- **Panels**: Various cockpit instruments (F/A-18C IFEI, RWR, SARI, MFCDs, etc.)

### 5️⃣ **Fine-Tune Offsets (Optional)**
Once a monitor is assigned, offset fields appear in the bottom-left corner:
- **X / Y**: Position offset in pixels (e.g., X:-50 shifts left by 50px)
- **W / H**: Override width/height (-1 = use original monitor size)

### 6️⃣ **Review Layout**
- The orange bounding box shows your total DCS resolution
- Labels show both Windows and DCS coordinates
- Assigned monitors change color (green for viewports, orange for panels)

### 7️⃣ **Save Your Configuration**
1. Click **"Export DCS Lua"**
2. Review the generated Lua code in the preview window
3. Either:
   - Use **"💾 Quick Save to DCS"** to save directly to your DCS folder
   - Or **"Save as..."** to save anywhere you want
4. **Two files are created:**
   - `YourLayout.lua` - The DCS configuration file
   - `YourLayout.dml` - Your complete setup (assignments, offsets, name, description)

### 8️⃣ **Load a Saved Layout**
1. Click **"📂 Load Layout"**
2. Select a `.dml` file (automatically opens in your DCS folder)
3. All settings are restored: name, description, assignments, and offsets
4. If your monitor configuration changed, you'll get a warning with details

### 9️⃣ **Configure DCS**
The exported `.lua` file goes into:
```
C:\DCS\DCS World\Config\MonitorSetup\YourLayout.lua
```

Then select it in DCS: **Options → System → Monitors → "YourLayout"**

---

## ⚙️ Configuration

### Global Config (config.json)
Click the **"⚙️ Config"** button to edit the global configuration file.

This file contains **only** the global DCS path:

```json
{
  "_dcs_monitor_setup_path": "C:\\DCS\\DCS World\\Config\\MonitorSetup",
  "_comment": "This is the global config. Only the DCS path is stored here. All other settings (name, description, offsets) are stored per-layout in .dml files."
}
```

**Why global?** This path is the same for all your monitor setups, so it only needs to be configured once.

---

### Per-Layout Settings (.dml files)

Each monitor layout is saved as a `.dml` (DCS Monitor Layout) file containing:

```json
{
  "version": "1.0",
  "name": "F18_Cockpit",
  "description": "My F/A-18C Multi-Monitor Setup",
  "monitor_assignments": {
    "MONITOR_1": "Viewport: Center",
    "MONITOR_2": "Viewport: Left",
    "MONITOR_3": "Panel: FA_18C_IFEI"
  },
  "monitor_offsets": {
    "MONITOR_1": {"x": 0, "y": 0, "width": -1, "height": -1},
    "MONITOR_2": {"x": -50, "y": 0, "width": 1920, "height": 1080},
    "MONITOR_3": {"x": 0, "y": 100, "width": -1, "height": -1}
  },
  "monitor_info": {
    "MONITOR_1": {"width": 2560, "height": 1440, "x": 0, "y": 0}
  }
}
```

### What's stored in .dml files?

- ✅ **Layout name and description** (from GUI fields)
- ✅ **Monitor assignments** (which monitor is which viewport/panel)
- ✅ **Per-monitor offsets** (X/Y position adjustments, W/H overrides)
- ✅ **Monitor validation data** (resolution and position for change detection)

### Benefits of .dml files:

- 📁 **One file = Complete setup** - Easy to backup, share, or switch between
- 🔄 **Multiple layouts** - Create different setups (streaming, racing, combat) and switch with one click
- ⚠️ **Change detection** - Warns you if monitor configuration changed since last save
- 🎯 **No conflicts** - Each layout has its own independent settings

---

## 🎮 Controls

| Action | Control |
|--------|---------|
| **Assign Monitor** | Click dropdown menu on monitor |
| **Adjust Offsets** | Edit X/Y/W/H fields (appear after assignment) |
| **Zoom In/Out** | `Ctrl` + Mouse Wheel |
| **Pan View** | Middle Mouse Button + Drag |
| **Bring Monitor to Front** | Click monitor or any field inside it |
| **Load Layout** | 📂 Button (loads .dml file) |
| **Refresh Monitors** | 🔄 Button (preserves assignments) |
| **Open Display Settings** | 🖥️ Button (opens Windows settings) |
| **Export Lua** | "Export DCS Lua" button |

---

## 🛠️ Supported Panels

### Viewports
- Left, Center, Right (3D world views)

### Default ViewPorts (Most Aircrafts support them)
- LEFT_MFCD, CENTER_MFCD, RIGHT_MFCD

### F/A-18C Panels
- IFEI, RWR, SARI


*More panels will be added in the Future also for different AirCrafts. Contact me and I will do my best to get it implemented as quick as I can.*

---

## 📦 Generated Files

The tool generates **two files** when you export:

### 1. `.lua` file (DCS Configuration)
This is the standard DCS MonitorSetup file that contains:
- `Viewports` table with all assigned viewports
- Individual panel definitions (e.g., `FA_18C_IFEI`, `LEFT_MFCD`)
- `Main` viewport (bounding box of all assigned monitors)
- Proper aspect ratios and coordinate calculations

**Example structure:**
```lua
_ = function(p) return p; end;
name = _('F18_Cockpit');
Description = 'My F/A-18C Multi-Monitor Setup'

Viewports =
{
    Center =
    {
        x = 0;
        y = 0;
        width = 2560;
        height = 1440;
        viewDx = 0;
        viewDy = 0;
        aspect = 1.777;
    },
}

FA_18C_IFEI =
{
    x = 2560;
    y = 0;
    width = 1920;
    height = 1080;
}
```

### 2. `.dml` file (Your Complete Setup)
This is the DCS Monitor Layout file that stores **everything**:
- Layout name and description
- All monitor assignments
- All offsets and overrides
- Monitor validation data (resolution, position)

**Purpose:** Load this file with the **"📂 Load Layout"** button to restore your complete setup instantly!

---

## 🐛 Troubleshooting

### Monitors not showing correctly?
- Click **"🔄 Refresh Monitor Layout"** to reload your Windows display configuration
- Check Windows Display Settings to ensure all monitors are detected
- Use **"🖥️ Windows Display Settings"** button to quickly access Windows settings

### Quick Save not working?
- Click **"⚙️ Config"** and verify `_dcs_monitor_setup_path` points to your DCS installation
- Ensure the folder exists and you have write permissions
- The path should look like: `C:\DCS\DCS World\Config\MonitorSetup`

### DCS not showing the configuration?
- Verify the `.lua` file is in: `DCS World\Config\MonitorSetup\`
- Restart DCS World after adding new configurations
- Check DCS logs for Lua syntax errors

### Load Layout warns about changes?
- Your Windows monitor setup changed since saving the .dml file
- Options:
  - **Load anyway** - Assignments will be restored, but coordinates may be off
  - **Cancel** - Rearrange monitors in Windows to match, then try again
  - **Create new layout** - Save the current setup as a new .dml file

### Dropdown menu behind another monitor?
- Click the monitor itself first to bring it to front
- Or click any input field (X/Y/W/H) to bring the monitor forward
- This should happen automatically, but overlapping monitors can cause issues

### Offset fields not appearing?
- Offset fields only appear **after** you assign a monitor to a viewport or panel
- If assigned but not visible, try reassigning from the dropdown

### Mouse wheel changes dropdown values accidentally?
- This is now disabled - dropdowns and input fields only respond to mouse wheel when focused
- Click the field first, then scroll

---

## 📝 License

This tool is provided as-is for the DCS community. Feel free to modify and share!

---

## 🤝 Contributing

Have ideas for new panels or features? Feel free to:
- Fork the repository
- Add your panels to the dropdown list
- Submit pull requests

---

## 🎯 Tips & Tricks

💡 **Tip 1**: Assign your main flight view to "Center" viewport for best performance  
💡 **Tip 2**: Use negative offsets (e.g., Y:-100) if panels appear too low/high  
💡 **Tip 3**: The tool preserves your assignments when refreshing - experiment freely!  
💡 **Tip 4**: Orange bounding box shows your total DCS resolution - keep it reasonable for performance  
💡 **Tip 5**: Save different .dml files for different aircraft or use cases (racing, combat, streaming)  
💡 **Tip 6**: Use Width/Height overrides (-1 = original) to render panels at different resolutions  
💡 **Tip 7**: Click **"📂 Load Layout"** to quickly switch between saved setups  
💡 **Tip 8**: The .dml file is just JSON - you can edit it manually if needed  
💡 **Tip 9**: Keep both .lua and .dml files together - they work as a pair  
💡 **Tip 10**: Monitor validation warns you if hardware changed - helps prevent broken configs  

---

## 📁 Workflow Example

**Creating a new setup:**
1. 🖥️ Arrange monitors in Windows
2. 🔄 Refresh Monitor Layout
3. ✏️ Enter layout name: "F18_Combat"
4. 🎯 Assign monitors (dropdowns)
5. 🔧 Adjust offsets if needed
6. 💾 Export → Quick Save to DCS
7. ✅ Both `F18_Combat.lua` and `F18_Combat.dml` are saved

**Switching setups:**
1. 📂 Load Layout
2. Select `StreamingSetup.dml`
3. ✅ Everything restored instantly
4. Make changes if needed
5. 💾 Export again

**Sharing with friends:**
1. Send them your `.dml` file
2. They load it with 📂 Load Layout
3. If their monitors are different, they get a warning
4. They can adjust offsets and save their own version  

---

**Made with ❤️ for the DCS Community by lxnx382**

🚁 Fly safe and enjoy your multi-monitor setup! 🚁
