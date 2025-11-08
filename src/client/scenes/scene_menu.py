# External libraries
from pyglet.shapes import Rectangle
from pyglet.text import Label

# Internal libraries
from client.scenes.scene import Scene
from client.display.batch_object import BatchObject
from common.config import LOGICAL_SCREEN_WIDTH, LOGICAL_SCREEN_HEIGHT
from common.logger import get_logger

logger = get_logger(__name__)


class SceneMenu(Scene):
    """Simple menu scene to pick a game mode at startup."""

    def __init__(self) -> None:
        super().__init__()
        self.buttons: list[dict] = []

    def helper_enter(self) -> None:
        """Create menu visuals: title and three buttons."""
        # Title
        self.title = self.add_to_batch(
            BatchObject(self.batch)
        )
        title_label = Label(
            "Arena Battle",
            x=LOGICAL_SCREEN_WIDTH // 2,
            y=LOGICAL_SCREEN_HEIGHT - 100,
            anchor_x="center",
            anchor_y="center",
            font_size=32,
            color=(255, 255, 255, 255),
            batch=self.batch,
        )
        self.title.register_sub_object(title_label)

        # Buttons (Survival, Option2, Option3)
        btn_w = 300
        btn_h = 48
        center_x = LOGICAL_SCREEN_WIDTH // 2
        start_y = LOGICAL_SCREEN_HEIGHT // 2 + 40
        labels = ["Survival", "Option2", "Option3"]

        for i, text in enumerate(labels):
            bx = center_x - btn_w // 2
            by = start_y - i * (btn_h + 16)

            btn_obj = BatchObject(self.batch)
            rect = Rectangle(x=bx, y=by, width=btn_w, height=btn_h, color=(80, 80, 120), batch=self.batch)
            lbl = Label(
                text,
                x=center_x,
                y=by + btn_h // 2,
                anchor_x="center",
                anchor_y="center",
                font_size=18,
                color=(255, 255, 255, 255),
                batch=self.batch,
            )
            btn_obj.register_sub_object(rect)
            btn_obj.register_sub_object(lbl)

            self.add_to_batch(btn_obj)

            # Store original text and disabled state to avoid repeated appends
            self.buttons.append({
                "rect": rect,
                "label": lbl,
                "name": text,
                "orig_text": text,
                "disabled": False,
            })

    def helper_update(self, dt: float) -> None:
        # Nothing dynamic for now
        self.cleanup_removed_objects()

    def helper_mouse_press(self, logical_x: float, logical_y: float, button: int, modifiers: int) -> None:
        """Handle clicks on buttons."""
        logger.debug("[Menu] Mouse press at (%.1f, %.1f), button=%s", logical_x, logical_y, button)

        for btn in self.buttons:
            # Ignore clicks on disabled buttons
            if btn.get("disabled"):
                continue

            r = btn["rect"]
            if r.x <= logical_x <= r.x + r.width and r.y <= logical_y <= r.y + r.height:
                name = btn["name"]
                logger.info("[Menu] Clicked button '%s'", name)
                if name == "Survival":
                    # Send ready to server and show waiting feedback
                    # Try to find the running main module's network_instance.
                    # When the client is run as a script its module name is '__main__',
                    # so check that first; otherwise fall back to 'client.main'.
                    import sys

                    network_instance = None
                    main_mod = sys.modules.get("__main__")
                    if main_mod is not None:
                        network_instance = getattr(main_mod, "network_instance", None)

                    if network_instance is None:
                        try:
                            import client.main as client_main_mod

                            network_instance = getattr(client_main_mod, "network_instance", None)
                        except Exception:
                            network_instance = None

                    logger.debug("[Menu] resolved network_instance=%s", network_instance)

                    # Always update UI immediately so user gets feedback
                    btn["label"].text = "Waiting for players..."
                    btn["rect"].color = (100, 100, 140)
                    btn["disabled"] = True

                    if network_instance:
                        try:
                            network_instance.send_ready()
                            logger.info("[Menu] Sent ready to server")
                        except Exception as e:
                            logger.exception("[Menu] Error sending ready: %s", e)
                    else:
                        # If no network available, fall back to local start
                        try:
                            # Try to use the already-resolved main_mod (which may be __main__)
                            if main_mod and getattr(main_mod, "window_instance", None):
                                if main_mod.window_instance and main_mod.window_instance.scene_manager:
                                    main_mod.window_instance.scene_manager.switch_to("gameplay")
                            else:
                                # Fallback: import client.main module
                                import client.main as client_main_mod
                                if client_main_mod.window_instance and client_main_mod.window_instance.scene_manager:
                                    client_main_mod.window_instance.scene_manager.switch_to("gameplay")
                        except Exception as e:
                            logger.exception("[Menu] Error switching to gameplay locally: %s", e)
                else:
                    # Not implemented feedback: set text once and disable
                    if not btn.get("disabled"):
                        btn["label"].text = btn["orig_text"] + " (Not implemented)"
                        btn["disabled"] = True
        