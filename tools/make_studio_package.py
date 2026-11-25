"""Packs the Character Studio scripts into NeonCoastCharacterStudio.rbxmx: python tools/make_studio_package.py
Drag the .rbxmx into ServerScriptService in Studio; LookStudioService moves the rest where it belongs on start."""
import os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS = [("ModuleScript", "NCLookCatalog", "NCLookCatalog.lua"), ("ModuleScript", "NCLookBuilder", "NCLookBuilder.lua"),
         ("Script", "LookStudioService", "LookStudioService.server.lua"), ("LocalScript", "LookStudioClient", "LookStudioClient.client.lua")]
out = ['<roblox version="4"><Item class="Folder" referent="RBX0"><Properties><string name="Name">NeonCoastCharacterStudio</string></Properties>']
for i, (cls, name, f) in enumerate(ITEMS, 1):
    src = open(os.path.join(root, f), encoding="utf-8").read().replace("]]>", "]]]]><![CDATA[>")
    out.append(f'<Item class="{cls}" referent="RBX{i}"><Properties><string name="Name">{name}</string>'
               f'<ProtectedString name="Source"><![CDATA[{src}]]></ProtectedString></Properties></Item>')
out.append("</Item></roblox>")
open(os.path.join(root, "NeonCoastCharacterStudio.rbxmx"), "w", encoding="utf-8").write("".join(out))
print("wrote NeonCoastCharacterStudio.rbxmx")
