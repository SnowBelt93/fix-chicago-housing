"""Render one illustration:  python tools/art/render.py <scene> <out.png> [width height samples]
Needs Blender's Python module (pip install bpy==5.0.1 on Python 3.11)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit, scenes

name, out = sys.argv[1], sys.argv[2]
w, h, samples = (int(a) for a in (sys.argv[3:6] + ["1280", "840", "64"][len(sys.argv[3:6]):]))
kit.reset()
cfg = getattr(scenes, name)()
kit.rig(cfg["ortho"], target=cfg["target"], elev=cfg.get("elev", 35), azim=cfg.get("azim", -45), sun=cfg.get("sun", (48, -30)))
kit.shadow_catcher(z=-3.25)
kit.render(os.path.abspath(out), w, h, samples=samples, transparent=cfg.get("transparent", True))
