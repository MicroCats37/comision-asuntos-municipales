---
excalidraw-plugin: parsed
---
# Diseño de Red - Ejemplo Excalidraw

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "claude-code",
  "elements": [
    {
      "id": "internet_cloud1",
      "type": "ellipse",
      "x": 460, "y": 30, "width": 90, "height": 55,
      "strokeColor": "#6b21a8", "backgroundColor": "#f3e8ff",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100001, "boundElements": null
    },
    {
      "id": "internet_cloud2",
      "type": "ellipse",
      "x": 510, "y": 20, "width": 100, "height": 60,
      "strokeColor": "#6b21a8", "backgroundColor": "#f3e8ff",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100002, "boundElements": null
    },
    {
      "id": "internet_cloud3",
      "type": "ellipse",
      "x": 565, "y": 35, "width": 80, "height": 50,
      "strokeColor": "#6b21a8", "backgroundColor": "#f3e8ff",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100003, "boundElements": null
    },
    {
      "id": "lbl_internet",
      "type": "text",
      "text": "Internet",
      "x": 500, "y": 58, "width": 90, "height": 30,
      "fontSize": 18, "fontFamily": 2, "textAlign": "center", "verticalAlign": "top",
      "strokeColor": "#1e293b", "seed": 100004, "containerId": null
    },
    {
      "id": "arrow_internet_fw",
      "type": "arrow",
      "x": 555, "y": 90, "width": 0, "height": 50,
      "strokeColor": "#475569", "fillStyle": "solid", "strokeWidth": 2,
      "roughness": 0, "opacity": 100, "seed": 100010,
      "points": [[0, 0], [0, 50]],
      "startBinding": { "elementId": "internet_cloud2", "gap": 10, "focus": 0 },
      "endBinding": { "elementId": "firewall", "gap": 5, "focus": 0 }
    },
    {
      "id": "firewall",
      "type": "rectangle",
      "x": 480, "y": 145, "width": 150, "height": 65,
      "strokeColor": "#991b1b", "backgroundColor": "#fee2e2",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100011,
      "boundElements": [
        { "id": "lbl_firewall", "type": "text" },
        { "id": "arrow_internet_fw", "type": "arrow" },
        { "id": "arrow_fw_router", "type": "arrow" }
      ]
    },
    {
      "id": "lbl_firewall",
      "type": "text",
      "text": "Firewall",
      "x": 480, "y": 163, "width": 150, "height": 30,
      "fontSize": 20, "fontFamily": 2, "textAlign": "center", "verticalAlign": "middle",
      "strokeColor": "#1e293b", "seed": 100012, "containerId": "firewall"
    },
    {
      "id": "arrow_fw_router",
      "type": "arrow",
      "x": 555, "y": 210, "width": 0, "height": 50,
      "strokeColor": "#475569", "fillStyle": "solid", "strokeWidth": 2,
      "roughness": 0, "opacity": 100, "seed": 100020,
      "points": [[0, 0], [0, 50]],
      "startBinding": { "elementId": "firewall", "gap": 5, "focus": 0 },
      "endBinding": { "elementId": "router", "gap": 5, "focus": 0 }
    },
    {
      "id": "router",
      "type": "rectangle",
      "x": 480, "y": 265, "width": 150, "height": 65,
      "strokeColor": "#854d0e", "backgroundColor": "#fef9c3",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100021,
      "boundElements": [
        { "id": "lbl_router", "type": "text" },
        { "id": "arrow_fw_router", "type": "arrow" },
        { "id": "arrow_router_switch", "type": "arrow" }
      ]
    },
    {
      "id": "lbl_router",
      "type": "text",
      "text": "Router",
      "x": 480, "y": 283, "width": 150, "height": 30,
      "fontSize": 20, "fontFamily": 2, "textAlign": "center", "verticalAlign": "middle",
      "strokeColor": "#1e293b", "seed": 100022, "containerId": "router"
    },
    {
      "id": "arrow_router_switch",
      "type": "arrow",
      "x": 555, "y": 330, "width": 0, "height": 50,
      "strokeColor": "#475569", "fillStyle": "solid", "strokeWidth": 2,
      "roughness": 0, "opacity": 100, "seed": 100030,
      "points": [[0, 0], [0, 50]],
      "startBinding": { "elementId": "router", "gap": 5, "focus": 0 },
      "endBinding": { "elementId": "switch_core", "gap": 5, "focus": 0 }
    },
    {
      "id": "switch_core",
      "type": "rectangle",
      "x": 480, "y": 385, "width": 150, "height": 65,
      "strokeColor": "#0369a1", "backgroundColor": "#e0f2fe",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100031,
      "boundElements": [
        { "id": "lbl_switch", "type": "text" },
        { "id": "arrow_router_switch", "type": "arrow" },
        { "id": "arrow_switch_vlan_users", "type": "arrow" },
        { "id": "arrow_switch_vlan_servers", "type": "arrow" }
      ]
    },
    {
      "id": "lbl_switch",
      "type": "text",
      "text": "Switch Core",
      "x": 480, "y": 403, "width": 150, "height": 30,
      "fontSize": 20, "fontFamily": 2, "textAlign": "center", "verticalAlign": "middle",
      "strokeColor": "#1e293b", "seed": 100032, "containerId": "switch_core"
    },
    {
      "id": "zone_vlan_users",
      "type": "rectangle",
      "x": 30, "y": 475, "width": 470, "height": 250,
      "strokeColor": "#475569", "backgroundColor": "#f1f5f9",
      "fillStyle": "solid", "strokeStyle": "dashed", "strokeWidth": 2,
      "roughness": 0, "opacity": 30, "seed": 100040, "boundElements": null
    },
    {
      "id": "lbl_vlan_users",
      "type": "text",
      "text": "VLAN Usuarios",
      "x": 46, "y": 487, "width": 200, "height": 30,
      "fontSize": 22, "fontFamily": 2, "textAlign": "left", "verticalAlign": "top",
      "strokeColor": "#334155", "seed": 100041, "containerId": null
    },
    {
      "id": "arrow_switch_vlan_users",
      "type": "arrow",
      "x": 480, "y": 450, "width": -250, "height": 0,
      "strokeColor": "#475569", "fillStyle": "solid", "strokeWidth": 2,
      "roughness": 0, "opacity": 100, "seed": 100050,
      "points": [[0, 0], [-250, 0]],
      "startBinding": { "elementId": "switch_core", "gap": 5, "focus": 0 },
      "endBinding": { "elementId": "pc1", "gap": 5, "focus": 0 }
    },
    {
      "id": "pc1_monitor",
      "type": "rectangle",
      "x": 70, "y": 530, "width": 80, "height": 60,
      "strokeColor": "#0369a1", "backgroundColor": "#e0f2fe",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100051, "boundElements": [
        { "id": "pc1_screen", "type": "rectangle" },
        { "id": "lbl_pc1", "type": "text" }
      ]
    },
    {
      "id": "pc1_screen",
      "type": "rectangle",
      "x": 76, "y": 536, "width": 68, "height": 42,
      "strokeColor": "#0369a1", "backgroundColor": "#bae6fd",
      "fillStyle": "solid", "strokeWidth": 1, "roughness": 0, "opacity": 100,
      "seed": 100052, "boundElements": null
    },
    {
      "id": "lbl_pc1",
      "type": "text",
      "text": "PC",
      "x": 70, "y": 596, "width": 80, "height": 20,
      "fontSize": 14, "fontFamily": 2, "textAlign": "center", "verticalAlign": "top",
      "strokeColor": "#334155", "seed": 100053, "containerId": null
    },
    {
      "id": "laptop_body",
      "type": "rectangle",
      "x": 195, "y": 545, "width": 110, "height": 70,
      "strokeColor": "#0369a1", "backgroundColor": "#e0f2fe",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100060, "boundElements": [
        { "id": "laptop_screen", "type": "rectangle" },
        { "id": "lbl_laptop", "type": "text" }
      ]
    },
    {
      "id": "laptop_screen",
      "type": "rectangle",
      "x": 201, "y": 551, "width": 98, "height": 52,
      "strokeColor": "#0369a1", "backgroundColor": "#bae6fd",
      "fillStyle": "solid", "strokeWidth": 1, "roughness": 0, "opacity": 100,
      "seed": 100061, "boundElements": null
    },
    {
      "id": "lbl_laptop",
      "type": "text",
      "text": "Laptop",
      "x": 195, "y": 621, "width": 110, "height": 20,
      "fontSize": 14, "fontFamily": 2, "textAlign": "center", "verticalAlign": "top",
      "strokeColor": "#334155", "seed": 100062, "containerId": null
    },
    {
      "id": "wifi_antenna",
      "type": "rectangle",
      "x": 370, "y": 530, "width": 80, "height": 70,
      "strokeColor": "#0369a1", "backgroundColor": "#e0f2fe",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100070, "boundElements": [
        { "id": "wifi_arc1", "type": "ellipse" },
        { "id": "wifi_arc2", "type": "ellipse" },
        { "id": "wifi_arc3", "type": "ellipse" },
        { "id": "lbl_wifi", "type": "text" }
      ]
    },
    {
      "id": "wifi_arc1",
      "type": "ellipse",
      "x": 370, "y": 502, "width": 80, "height": 28,
      "strokeColor": "#0369a1", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100071, "boundElements": null
    },
    {
      "id": "wifi_arc2",
      "type": "ellipse",
      "x": 362, "y": 490, "width": 96, "height": 32,
      "strokeColor": "#0369a1", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100072, "boundElements": null
    },
    {
      "id": "wifi_arc3",
      "type": "ellipse",
      "x": 354, "y": 478, "width": 112, "height": 36,
      "strokeColor": "#0369a1", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100073, "boundElements": null
    },
    {
      "id": "lbl_wifi",
      "type": "text",
      "text": "WiFi",
      "x": 370, "y": 605, "width": 80, "height": 20,
      "fontSize": 14, "fontFamily": 2, "textAlign": "center", "verticalAlign": "top",
      "strokeColor": "#334155", "seed": 100074, "containerId": null
    },
    {
      "id": "zone_vlan_servers",
      "type": "rectangle",
      "x": 530, "y": 475, "width": 450, "height": 250,
      "strokeColor": "#475569", "backgroundColor": "#f1f5f9",
      "fillStyle": "solid", "strokeStyle": "dashed", "strokeWidth": 2,
      "roughness": 0, "opacity": 30, "seed": 100080, "boundElements": null
    },
    {
      "id": "lbl_vlan_servers",
      "type": "text",
      "text": "VLAN Servidores",
      "x": 546, "y": 487, "width": 220, "height": 30,
      "fontSize": 22, "fontFamily": 2, "textAlign": "left", "verticalAlign": "top",
      "strokeColor": "#334155", "seed": 100081, "containerId": null
    },
    {
      "id": "arrow_switch_vlan_servers",
      "type": "arrow",
      "x": 630, "y": 450, "width": 190, "height": 0,
      "strokeColor": "#475569", "fillStyle": "solid", "strokeWidth": 2,
      "roughness": 0, "opacity": 100, "seed": 100090,
      "points": [[0, 0], [190, 0]],
      "startBinding": { "elementId": "switch_core", "gap": 5, "focus": 0 },
      "endBinding": { "elementId": "server_app", "gap": 5, "focus": 0 }
    },
    {
      "id": "server_app",
      "type": "rectangle",
      "x": 560, "y": 530, "width": 130, "height": 80,
      "strokeColor": "#166534", "backgroundColor": "#dcfce7",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100091,
      "boundElements": [
        { "id": "lbl_server_app", "type": "text" },
        { "id": "arrow_app_db", "type": "arrow" }
      ]
    },
    {
      "id": "lbl_server_app",
      "type": "text",
      "text": "Servidor App",
      "x": 560, "y": 556, "width": 130, "height": 28,
      "fontSize": 16, "fontFamily": 2, "textAlign": "center", "verticalAlign": "middle",
      "strokeColor": "#1e293b", "seed": 100092, "containerId": "server_app"
    },
    {
      "id": "db_ellipse_top",
      "type": "ellipse",
      "x": 725, "y": 530, "width": 130, "height": 35,
      "strokeColor": "#6b21a8", "backgroundColor": "#f3e8ff",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100100, "boundElements": null
    },
    {
      "id": "db_body",
      "type": "rectangle",
      "x": 725, "y": 552, "width": 130, "height": 58,
      "strokeColor": "#6b21a8", "backgroundColor": "#f3e8ff",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100101,
      "boundElements": [
        { "id": "db_ellipse_top", "type": "ellipse" },
        { "id": "lbl_db", "type": "text" }
      ]
    },
    {
      "id": "lbl_db",
      "type": "text",
      "text": "Base de Datos",
      "x": 725, "y": 568, "width": 130, "height": 28,
      "fontSize": 16, "fontFamily": 2, "textAlign": "center", "verticalAlign": "middle",
      "strokeColor": "#1e293b", "seed": 100102, "containerId": "db_body"
    },
    {
      "id": "arrow_app_db",
      "type": "arrow",
      "x": 690, "y": 570, "width": 35, "height": 0,
      "strokeColor": "#475569", "fillStyle": "solid", "strokeWidth": 2,
      "roughness": 0, "opacity": 100, "seed": 100110,
      "points": [[0, 0], [35, 0]],
      "startBinding": { "elementId": "server_app", "gap": 5, "focus": 0 },
      "endBinding": { "elementId": "db_body", "gap": 5, "focus": 0 }
    },
    {
      "id": "nas_server",
      "type": "rectangle",
      "x": 560, "y": 640, "width": 130, "height": 70,
      "strokeColor": "#854d0e", "backgroundColor": "#fef9c3",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
      "seed": 100120,
      "boundElements": [
        { "id": "nas_bay1", "type": "rectangle" },
        { "id": "nas_bay2", "type": "rectangle" },
        { "id": "lbl_nas", "type": "text" }
      ]
    },
    {
      "id": "nas_bay1",
      "type": "rectangle",
      "x": 568, "y": 648, "width": 114, "height": 18,
      "strokeColor": "#854d0e", "backgroundColor": "#fef3c7",
      "fillStyle": "solid", "strokeWidth": 1, "roughness": 0, "opacity": 100,
      "seed": 100121, "boundElements": null
    },
    {
      "id": "nas_bay2",
      "type": "rectangle",
      "x": 568, "y": 672, "width": 114, "height": 18,
      "strokeColor": "#854d0e", "backgroundColor": "#fef3c7",
      "fillStyle": "solid", "strokeWidth": 1, "roughness": 0, "opacity": 100,
      "seed": 100122, "boundElements": null
    },
    {
      "id": "lbl_nas",
      "type": "text",
      "text": "NAS / Backup",
      "x": 560, "y": 716, "width": 130, "height": 20,
      "fontSize": 14, "fontFamily": 2, "textAlign": "center", "verticalAlign": "top",
      "strokeColor": "#334155", "seed": 100123, "containerId": null
    },
    {
      "id": "lbl_title",
      "type": "text",
      "text": "Diseño de Red Corporativa",
      "x": 30, "y": 10, "width": 400, "height": 40,
      "fontSize": 28, "fontFamily": 2, "textAlign": "left", "verticalAlign": "top",
      "strokeColor": "#1e293b", "seed": 100001, "containerId": null
    }
  ],
  "appState": { "viewBackgroundColor": "#ffffff" }
}
```
