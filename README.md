import pygame
from pygame import sprite, transform, image, display, event, key, time, font
from pygame.locals import K_UP, K_DOWN, K_w, K_s, K_q, K_e, K_ESCAPE, QUIT, FULLSCREEN
import random
import json
import os
from enum import Enum

"""Game Configuration"""
CONFIG = {
    "win_width": 600,
    "win_height": 500,
    "paddle_width": 50,
    "paddle_height": 150,
    "ball_size": 50,
    "initial_ball_speed": 3,
    "max_ball_speed": 8,
    "paddle_speed": 4,
    "ai_difficulty": "medium",  # easy, medium, hard
    "trail_length": 15,
    "trail_color": (255, 200, 0),
    "background_color": (200, 255, 255),
    "fullscreen": False,
}

# Skills Configuration
SKILLS_CONFIG = {
    "speed_boost": {
        "name": "Speed Boost",
        "key": K_q,
        "cooldown": 600,
        "duration": 180,
        "description": "Increase paddle speed by 50%",
        "color": (100, 200, 255),
    },
    "paddle_grow": {
        "name": "Paddle Grow",
        "key": K_e,
        "cooldown": 600,
        "duration": 150,
        "description": "Enlarge paddle by 50%",
        "color": (100, 255, 100),
    },
    "shield": {
        "name": "Shield",
        "key": pygame.K_r,
        "cooldown": 800,
        "duration": 300,
        "description": "Block one goal attempt",
        "color": (255, 200, 100),
    },
}


# AI Special Skills — unique per bot, not available to player
AI_SKILLS_CONFIG = {
    "glitch_teleport": {
        "name": "Glitch Teleport",
        "cooldown": 480,       # 8 seconds
        "duration": 1,         # instant
        "description": "Ball teleports to a random position",
        "color": (180, 80, 255),
        "owner": "easy",
    },
    "overclock": {
        "name": "Overclock",
        "cooldown": 540,       # 9 seconds
        "duration": 200,       # ~3.3 seconds
        "description": "AI speed and ball speed surge",
        "color": (255, 160, 0),
        "owner": "medium",
    },
    "phase_cloak": {
        "name": "Phase Cloak",
        "cooldown": 600,       # 10 seconds
        "duration": 180,       # 3 seconds
        "description": "Ball turns invisible",
        "color": (80, 80, 200),
        "owner": "hard",
    },
    "phantom_ball": {
        "name": "Phantom Ball",
        "cooldown": 700,       # ~12 seconds
        "duration": 240,       # 4 seconds
        "description": "Spawns a fake decoy ball",
        "color": (180, 0, 180),
        "owner": "hard",
    },
}


# ── Shop Items — purchasable player skills ─────────────────────────────────────
SHOP_ITEMS = {
    "ball_control": {
        "name": "Ball Control",
        "key": pygame.K_z,
        "price": 150,
        "cooldown": 480,
        "duration": 1,           # instant effect on next bounce
        "description": "Next ball bounce deflects to your aim",
        "detail": "After hitting your paddle, press Z to\nsnap ball toward opponent's corner!",
        "color": (80, 200, 255),
        "icon": "B",
    },
    "time_slow": {
        "name": "Time Slow",
        "key": pygame.K_x,
        "price": 200,
        "cooldown": 600,
        "duration": 180,         # 3 seconds at 60 FPS
        "description": "Slows everything by 50% for 3s",
        "detail": "Ball and AI paddle halved in speed.\nYou move at full speed!",
        "color": (200, 150, 255),
        "icon": "T",
    },
    "shooting_star": {
        "name": "Shooting Star",
        "key": pygame.K_c,
        "price": 250,
        "cooldown": 720,
        "duration": 120,         # 2 seconds
        "description": "Ball goes blazing fast & straight",
        "detail": "Ball becomes a laser — 3x speed,\nstraight line, ignores spin!",
        "color": (255, 220, 50),
        "icon": "★",
    },
}

# Koen rewards per difficulty win
KOEN_REWARDS = {
    "easy":   {"base": 10, "rally_bonus": 0.5,  "combo_bonus": 1},
    "medium": {"base": 25, "rally_bonus": 1.0,  "combo_bonus": 2},
    "hard":   {"base": 50, "rally_bonus": 2.0,  "combo_bonus": 3},
}


class SaveManager:
    """Handles persistent save data (koen + owned skills) via JSON file."""
    SAVE_FILE = "pong_save.json"

    def __init__(self):
        self.koen = 0
        self.owned_skills = []   # list of skill keys e.g. ["ball_control"]
        self.load()

    def load(self):
        try:
            if os.path.exists(self.SAVE_FILE):
                with open(self.SAVE_FILE, "r") as f:
                    data = json.load(f)
                self.koen = data.get("koen", 0)
                self.owned_skills = data.get("owned_skills", [])
        except Exception:
            self.koen = 0
            self.owned_skills = []

    def save(self):
        try:
            with open(self.SAVE_FILE, "w") as f:
                json.dump({"koen": self.koen, "owned_skills": self.owned_skills}, f)
        except Exception:
            pass

    def earn_koen(self, amount):
        self.koen += amount
        self.save()

    def buy(self, skill_key):
        item = SHOP_ITEMS.get(skill_key)
        if not item:
            return False, "Unknown skill"
        if skill_key in self.owned_skills:
            return False, "Already owned!"
        if self.koen < item["price"]:
            return False, f"Need {item['price'] - self.koen} more koen"
        self.koen -= item["price"]
        self.owned_skills.append(skill_key)
        self.save()
        return True, f"Bought {item['name']}!"


    MAIN_MENU = 0
    INTRO = 1
    CHARACTER_SELECT = 2
    PRE_MATCH = 3
    PLAYING = 4
    PAUSED = 5
    GAME_OVER = 6
    ENDING = 7
    MULTIPLAYER_MENU = 8
    SHOP = 9


STORY = {
    "intro": {
        "title": "PONG CHAMPIONS LEAGUE",
        "subtitle": "A Tale of Pixel Glory",
        "text": [
            "You are a legendary Pong player who retired from",
            "professional tournaments 10 years ago.",
            "",
            "Now, mysterious challengers have appeared,",
            "challenging you to prove you're still the best!",
            "",
            "Can you reclaim your title as the Pong Champion?"
        ]
    },
    "character_select": {
        "title": "Choose Your Opponent",
        "opponents": {
            "1": {
                "name": "Circuit Bot - EASY",
                "description": "A beginner AI. Slow but steady.",
                "difficulty": "easy",
                "color": (100, 200, 100)
            },
            "2": {
                "name": "Cyber Runner - MEDIUM",
                "description": "A balanced challenger. Good reflexes.",
                "difficulty": "medium",
                "color": (200, 200, 100)
            },
            "3": {
                "name": "Shadow Master - HARD",
                "description": "Legendary opponent. Lightning fast!",
                "difficulty": "hard",
                "color": (255, 100, 100)
            }
        }
    },
    "opponent_dialogs": {
        "easy": [
            "Beep boop! I am Circuit Bot!",
            "I'm learning to play Pong...",
            "Let's have a friendly match!"
        ],
        "medium": [
            "I am Cyber Runner!",
            "I've trained my reflexes to perfection.",
            "Your skills are no match for me!"
        ],
        "hard": [
            "You have returned...",
            "I am Shadow Master, keeper of the Pong throne.",
            "Prepare yourself for ultimate defeat!"
        ]
    },
    "between_rounds": {
        "easy": [
            "Wow! You beat Circuit Bot!",
            "But greater challenges await you..."
        ],
        "medium": [
            "Impressive! You defeated Cyber Runner!",
            "But the ultimate test still lies ahead..."
        ],
        "hard": [
            "IMPOSSIBLE! You defeated Shadow Master!",
            "You have proven yourself worthy..."
        ]
    },
    "victory": {
        "title": "YOU ARE THE CHAMPION!",
        "text": [
            "You have defeated all challengers!",
            "Your legacy has been restored!",
            "",
            "The Pong Champions League bows before you.",
            "Your name will be remembered in legend.",
            "",
            "CONGRATULATIONS, CHAMPION!"
        ]
    },
    "defeat": {
        "title": "DEFEAT",
        "text": [
            "You have fallen in battle...",
            "But a true champion never gives up!",
            "",
            "Try again and reclaim your glory!"
        ]
    }
}


class GameSprite(sprite.Sprite):
    def __init__(self, player_image, player_x, player_y, player_speed, width, height):
        super().__init__()
        self.image = transform.scale(image.load(player_image), (width, height))
        self.speed = player_speed
        self.rect = self.image.get_rect()
        self.rect.x = player_x
        self.rect.y = player_y

    def reset(self):
        window.blit(self.image, (self.rect.x, self.rect.y))


class Ball(GameSprite):
    def __init__(self, player_image, player_x, player_y, player_speed, width, height):
        super().__init__(player_image, player_x, player_y, player_speed, width, height)
        self.trail = []
        self.trail_length = CONFIG["trail_length"]
        self.trail_color = CONFIG["trail_color"]
        self.trail_radius = 3
        self.rotation_angle = 0
        self.original_image = self.image
        self.invisible = False   # set True by Shadow Master's Phase Cloak

    def update_trail(self):
        self.trail.append((self.rect.centerx, self.rect.centery))
        if len(self.trail) > self.trail_length:
            self.trail.pop(0)

    def draw_trail(self):
        if self.invisible:
            return   # hide trail too when phase cloaked
        for i, (x, y) in enumerate(self.trail):
            alpha = int(255 * (i / len(self.trail))) if len(self.trail) > 0 else 255
            trail_surface = pygame.Surface((self.trail_radius * 2, self.trail_radius * 2))
            trail_surface.set_colorkey((0, 0, 0))
            trail_surface.fill((0, 0, 0))
            pygame.draw.circle(trail_surface, self.trail_color, (self.trail_radius, self.trail_radius), self.trail_radius)
            trail_surface.set_alpha(alpha)
            window.blit(trail_surface, (x - self.trail_radius, y - self.trail_radius))

    def rotate(self, speed_x, speed_y):
        self.rotation_angle = (self.rotation_angle + 10) % 360
        self.image = transform.rotate(self.original_image, self.rotation_angle)
        self.rect = self.image.get_rect(center=self.rect.center)

    def reset(self):
        if not self.invisible:
            window.blit(self.image, (self.rect.x, self.rect.y))

    def reset_position(self):
        self.rect.x = CONFIG["win_width"] // 2
        self.rect.y = CONFIG["win_height"] // 2
        self.trail = []
        self.rotation_angle = 0
        self.invisible = False


class FakeBall:
    """
    Phantom Ball — a decoy spawned by Shadow Master.
    Moves independently with its own velocity. Has a trail in a different
    color so it looks convincing. When it hits a wall or paddle it bounces
    normally, but scoring with it does nothing — it just vanishes.
    The player cannot tell which ball is real until one scores.
    """
    def __init__(self, x, y, vx, vy, size):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.size = size
        self.rect = pygame.Rect(int(self.x), int(self.y), size, size)
        self.trail = []
        self.trail_length = CONFIG["trail_length"]
        self.rotation_angle = 0
        # Load & scale same ball image but tint it purple-ish
        raw = image.load("tenis_ball.png")
        self.base_image = transform.scale(raw, (size, size))
        # Apply a purple tint overlay to distinguish from real ball
        tint = pygame.Surface((size, size), pygame.SRCALPHA)
        tint.fill((140, 0, 200, 100))
        self.base_image.blit(tint, (0, 0))
        self.image = self.base_image.copy()
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

        # Wall bounce
        if self.rect.y < 0 or self.rect.y > CONFIG["win_height"] - self.size:
            self.vy *= -1

        # Paddle bounce (visual only — no scoring)
        if self.rect.colliderect(racket1.rect) and self.vx < 0:
            self.vx = abs(self.vx)
            self.rect.left = racket1.rect.right + 1
        if self.rect.colliderect(racket2.rect) and self.vx > 0:
            self.vx = -abs(self.vx)
            self.rect.right = racket2.rect.left - 1

        # Vanish when it exits the screen
        if self.rect.x < -self.size or self.rect.x > CONFIG["win_width"] + self.size:
            self.alive = False

        # Trail
        self.trail.append((self.rect.centerx, self.rect.centery))
        if len(self.trail) > self.trail_length:
            self.trail.pop(0)

        # Rotation
        self.rotation_angle = (self.rotation_angle + 10) % 360
        self.image = transform.rotate(self.base_image, self.rotation_angle)
        self.rect = self.image.get_rect(center=self.rect.center)

    def draw(self):
        # Draw trail in purple
        trail_color = (180, 0, 220)
        trail_radius = 3
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(255 * (i / max(len(self.trail), 1)))
            surf = pygame.Surface((trail_radius * 2, trail_radius * 2))
            surf.set_colorkey((0, 0, 0))
            pygame.draw.circle(surf, trail_color, (trail_radius, trail_radius), trail_radius)
            surf.set_alpha(alpha)
            window.blit(surf, (tx - trail_radius, ty - trail_radius))
        window.blit(self.image, self.rect.topleft)


class Player(GameSprite):
    def __init__(self, player_image, player_x, player_y, player_speed, width, height, is_ai=False):
        super().__init__(player_image, player_x, player_y, player_speed, width, height)
        self.is_ai = is_ai
        self.ai_difficulty = CONFIG["ai_difficulty"]

        self.original_width = width
        self.original_height = height
        self.original_speed = player_speed
        self.original_image = self.image.copy()

        self.available_skills = ["speed_boost", "paddle_grow", "shield"]
        self.skill_cooldowns = {skill: 0 for skill in self.available_skills}
        self.skill_ready = {skill: True for skill in self.available_skills}
        self.active_skills = {}
        self.shield_active = False
        self.ai_skill_timer = random.randint(100, 200)

        # Shop skills — loaded from save_manager at match start
        self.shop_skill_cooldowns = {s: 0 for s in SHOP_ITEMS}
        self.shop_skill_ready = {s: True for s in SHOP_ITEMS}
        self.shop_skill_active = {}   # {skill: frames_remaining}
        # Flags for active effects
        self.ball_control_armed = False   # waiting for next paddle hit
        self.time_slow_active = False
        self.shooting_star_active = False

        # AI special skills — keyed by difficulty
        self.ai_special_skills = {
            "easy":   ["glitch_teleport"],
            "medium": ["overclock"],
            "hard":   ["phase_cloak", "phantom_ball"],
        }
        # Cooldown tracker for AI special skills  {skill_name: frames_remaining}
        self.ai_special_cooldowns = {s: 0 for s in AI_SKILLS_CONFIG}
        self.ai_special_ready = {s: True for s in AI_SKILLS_CONFIG}
        # Active duration tracker  {skill_name: frames_remaining}
        self.ai_special_active = {}
        self.ai_special_timer = random.randint(200, 400)

    def use_skill(self, skill_name):
        if skill_name not in self.available_skills:
            return False
        if self.skill_ready[skill_name]:
            self.activate_skill(skill_name)
            skill_config = SKILLS_CONFIG[skill_name]
            self.skill_cooldowns[skill_name] = skill_config["cooldown"]
            self.skill_ready[skill_name] = False
            return True
        return False

    def activate_skill(self, skill_name):
        skill_config = SKILLS_CONFIG[skill_name]
        duration = skill_config["duration"]

        if skill_name == "speed_boost":
            self.speed = self.original_speed * 1.5
            self.active_skills[skill_name] = duration
            sound_manager.play_sound("skill_activate")

        elif skill_name == "paddle_grow":
            # BUG FIX #3: Rescale the actual image so the paddle visually grows too
            new_height = int(self.original_height * 1.5)
            self.image = transform.scale(self.original_image, (self.original_width, new_height))
            self.rect = self.image.get_rect(topleft=self.rect.topleft)
            self.rect.height = new_height
            self.active_skills[skill_name] = duration
            sound_manager.play_sound("skill_activate")

        elif skill_name == "shield":
            self.shield_active = True
            self.active_skills[skill_name] = duration
            sound_manager.play_sound("skill_activate")

    def update_skills(self):
        for skill in self.available_skills:
            if not self.skill_ready[skill]:
                self.skill_cooldowns[skill] -= 1
                if self.skill_cooldowns[skill] <= 0:
                    self.skill_ready[skill] = True
                    self.skill_cooldowns[skill] = 0

        for skill in list(self.active_skills.keys()):
            self.active_skills[skill] -= 1
            if self.active_skills[skill] <= 0:
                self.deactivate_skill(skill)
                del self.active_skills[skill]

        # Tick shop skill cooldowns & durations
        for skill in SHOP_ITEMS:
            if not self.shop_skill_ready[skill]:
                self.shop_skill_cooldowns[skill] -= 1
                if self.shop_skill_cooldowns[skill] <= 0:
                    self.shop_skill_ready[skill] = True
                    self.shop_skill_cooldowns[skill] = 0

        for skill in list(self.shop_skill_active.keys()):
            self.shop_skill_active[skill] -= 1
            if self.shop_skill_active[skill] <= 0:
                self.deactivate_shop_skill(skill)
                del self.shop_skill_active[skill]

    def use_shop_skill(self, skill_key):
        """Activate a purchased shop skill."""
        if skill_key not in save_manager.owned_skills:
            return False
        if not self.shop_skill_ready[skill_key]:
            return False

        item = SHOP_ITEMS[skill_key]
        self.shop_skill_cooldowns[skill_key] = item["cooldown"]
        self.shop_skill_ready[skill_key] = False
        sound_manager.play_sound("skill_activate")

        if skill_key == "ball_control":
            # Arms the deflect — triggers on next paddle collision
            self.ball_control_armed = True
            # Duration tracks how long the "armed" window lasts
            self.shop_skill_active[skill_key] = item["duration"] if item["duration"] > 1 else 300

        elif skill_key == "time_slow":
            self.time_slow_active = True
            self.shop_skill_active[skill_key] = item["duration"]
            game_manager.flash_effect = {"color": (200, 150, 255), "timer": 12}

        elif skill_key == "shooting_star":
            self.shooting_star_active = True
            self.shop_skill_active[skill_key] = item["duration"]
            game_manager.flash_effect = {"color": (255, 220, 50), "timer": 12}
            # Immediately boost ball speed & lock direction
            global speed_x, speed_y
            magnitude = (speed_x**2 + speed_y**2) ** 0.5
            direction = 1 if speed_x > 0 else -1
            speed_x = direction * CONFIG["max_ball_speed"] * 1.5
            speed_y = 0   # straight line

        return True

    def deactivate_shop_skill(self, skill_key):
        """Remove shop skill effects."""
        if skill_key == "ball_control":
            self.ball_control_armed = False
        elif skill_key == "time_slow":
            self.time_slow_active = False
        elif skill_key == "shooting_star":
            self.shooting_star_active = False
            # Restore normal speed direction (keep current direction)
            global speed_x, speed_y
            direction = 1 if speed_x > 0 else -1
            speed_x = direction * CONFIG["initial_ball_speed"]
            speed_y = CONFIG["initial_ball_speed"] * random.choice([-0.8, 0.8])

    def on_paddle_hit_shop_skills(self):
        """Called when this player's paddle hits the ball — triggers ball_control."""
        if self.ball_control_armed:
            global speed_y
            # Deflect ball toward AI's top or bottom corner based on AI position
            ai_center = racket2.rect.centery
            field_mid = CONFIG["win_height"] // 2
            # Aim opposite to where AI is
            if ai_center < field_mid:
                speed_y = abs(speed_y) * 1.2   # aim low
            else:
                speed_y = -abs(speed_y) * 1.2  # aim high
            self.ball_control_armed = False
            if "ball_control" in self.shop_skill_active:
                del self.shop_skill_active["ball_control"]

    def deactivate_skill(self, skill_name):
        if skill_name == "speed_boost":
            self.speed = self.original_speed

        elif skill_name == "paddle_grow":
            # BUG FIX #3: Restore original image on deactivate
            self.image = self.original_image.copy()
            self.rect = self.image.get_rect(topleft=self.rect.topleft)
            self.rect.height = self.original_height

        elif skill_name == "shield":
            self.shield_active = False

    def use_shield(self):
        """
        BUG FIX #6: Shield now properly resets cooldown state when consumed.
        Previously, removing from active_skills while cooldown timer was still
        running caused the shield to go on cooldown without full duration played.
        """
        if self.shield_active:
            self.shield_active = False
            if "shield" in self.active_skills:
                del self.active_skills["shield"]
            # Properly trigger the cooldown from this moment
            self.skill_ready["shield"] = False
            self.skill_cooldowns["shield"] = SKILLS_CONFIG["shield"]["cooldown"]
            return True
        return False

    def ai_use_skill(self, gm):
        if self.is_ai:
            self.ai_skill_timer -= 1
            if self.ai_skill_timer <= 0:
                available = [s for s in self.available_skills if self.skill_ready[s]]
                if available:
                    if gm.player2_score < gm.player1_score and "shield" in available:
                        self.use_skill("shield")
                    elif gm.player2_score > gm.player1_score and "speed_boost" in available:
                        self.use_skill("speed_boost")
                    else:
                        self.use_skill(random.choice(available))
                self.ai_skill_timer = random.randint(150, 400)

    def update_ai_special_skills(self):
        """Tick cooldowns and active durations for AI special skills."""
        for skill in AI_SKILLS_CONFIG:
            if not self.ai_special_ready[skill]:
                self.ai_special_cooldowns[skill] -= 1
                if self.ai_special_cooldowns[skill] <= 0:
                    self.ai_special_ready[skill] = True
                    self.ai_special_cooldowns[skill] = 0

        for skill in list(self.ai_special_active.keys()):
            self.ai_special_active[skill] -= 1
            if self.ai_special_active[skill] <= 0:
                self.deactivate_ai_special(skill)
                del self.ai_special_active[skill]

    def try_use_ai_special(self, gm):
        """AI decides when to fire its special skill."""
        if not self.is_ai:
            return

        self.ai_special_timer -= 1
        if self.ai_special_timer > 0:
            return

        my_specials = self.ai_special_skills.get(self.ai_difficulty, [])
        ready = [s for s in my_specials if self.ai_special_ready[s]]
        if not ready:
            self.ai_special_timer = random.randint(120, 300)
            return

        chosen = random.choice(ready)

        # Difficulty-specific trigger logic
        if self.ai_difficulty == "easy":
            # Circuit Bot fires randomly regardless of score
            self.activate_ai_special(chosen, gm)

        elif self.ai_difficulty == "medium":
            # Cyber Runner overclock when ball is coming toward AI
            if gm.speed_x_ref is not None and gm.speed_x_ref < 0:
                self.activate_ai_special(chosen, gm)

        elif self.ai_difficulty == "hard":
            # Shadow Master uses skills strategically
            # phase_cloak when player is close to catching up
            # phantom_ball more aggressively
            if chosen == "phase_cloak" and gm.player1_score >= gm.player2_score - 2:
                self.activate_ai_special(chosen, gm)
            elif chosen == "phantom_ball":
                self.activate_ai_special(chosen, gm)

        self.ai_special_timer = random.randint(180, 360)

    def activate_ai_special(self, skill_name, gm):
        """Apply the AI special skill effect."""
        cfg = AI_SKILLS_CONFIG[skill_name]
        duration = cfg["duration"]

        if skill_name == "glitch_teleport":
            # Instantly teleport ball to a random position on the field
            margin = 80
            ball.rect.x = random.randint(margin, CONFIG["win_width"] - margin)
            ball.rect.y = random.randint(margin, CONFIG["win_height"] - margin)
            ball.trail = []
            # Also randomize vertical direction a bit
            global speed_y
            speed_y = abs(speed_y) * random.choice([-1, 1])
            # Show flash effect via game manager flag
            gm.flash_effect = {"color": (180, 80, 255), "timer": 12}

        elif skill_name == "overclock":
            # AI paddle surges + ball speeds up
            self.speed = self.original_speed * 2.2
            self.ai_special_active[skill_name] = duration
            gm.flash_effect = {"color": (255, 160, 0), "timer": 12}
            # Temporarily boost ball speed
            global speed_x
            speed_scale = 1.4
            speed_x *= speed_scale
            speed_y *= speed_scale
            gm.overclock_ball_scale = speed_scale  # remember so we can undo it

        elif skill_name == "phase_cloak":
            # Make the real ball invisible
            ball.invisible = True
            self.ai_special_active[skill_name] = duration
            gm.flash_effect = {"color": (80, 80, 200), "timer": 12}

        elif skill_name == "phantom_ball":
            # Spawn a fake ball travelling in a diverging direction
            offset_vy = speed_y * random.uniform(0.8, 1.5) * random.choice([-1, 1])
            fake = FakeBall(
                ball.rect.x, ball.rect.y,
                speed_x * random.uniform(0.9, 1.1),
                offset_vy,
                CONFIG["ball_size"]
            )
            gm.fake_balls.append(fake)
            self.ai_special_active[skill_name] = duration
            gm.flash_effect = {"color": (180, 0, 180), "timer": 12}

        # Start cooldown
        self.ai_special_ready[skill_name] = False
        self.ai_special_cooldowns[skill_name] = cfg["cooldown"]
        sound_manager.play_sound("skill_activate")

    def deactivate_ai_special(self, skill_name):
        """Remove AI special skill effects."""
        if skill_name == "overclock":
            self.speed = self.original_speed
            # Undo the ball speed boost (stored scale in game_manager handled in loop)

        elif skill_name == "phase_cloak":
            ball.invisible = False

    def update_r(self, gm):
        if self.is_ai:
            # Time Slow reduces AI reaction speed
            slow = 0.5 if (hasattr(racket1, 'time_slow_active') and racket1.time_slow_active) else 1.0
            orig = self.speed
            self.speed = self.speed * slow
            self.ai_move(ball)
            self.speed = orig
            self.ai_use_skill(gm)
            self.update_ai_special_skills()
            self.try_use_ai_special(gm)
        else:
            keys = key.get_pressed()
            if keys[K_UP] and self.rect.y > 5:
                self.rect.y -= self.speed
            if keys[K_DOWN] and self.rect.y < CONFIG["win_height"] - 80:
                self.rect.y += self.speed

    def update_l(self):
        keys = key.get_pressed()
        if keys[K_w] and self.rect.y > 5:
            self.rect.y -= self.speed
        if keys[K_s] and self.rect.y < CONFIG["win_height"] - 80:
            self.rect.y += self.speed

    def ai_move(self, ball):
        paddle_center = self.rect.centery
        ball_center = ball.rect.centery

        if self.ai_difficulty == "easy":
            reaction_speed = self.speed * 0.6
            error_margin = 50
        elif self.ai_difficulty == "medium":
            reaction_speed = self.speed * 0.85
            error_margin = 20
        else:
            reaction_speed = self.speed
            error_margin = 5

        target = ball_center + random.randint(-error_margin, error_margin)

        if paddle_center < target - 5 and self.rect.y < CONFIG["win_height"] - 80:
            self.rect.y += reaction_speed
        elif paddle_center > target + 5 and self.rect.y > 5:
            self.rect.y -= reaction_speed


class GameManager:
    def __init__(self, single_player=False, multiplayer=False):
        self.state = GameState.MAIN_MENU
        self.player1_score = 0
        self.player2_score = 0
        self.combo_counter = 0
        self.longest_rally = 0
        self.current_rally = 0
        self.single_player = single_player
        self.multiplayer = multiplayer
        self.game_over = False
        self.winner = None
        self.best_of = 3
        # BUG FIX #2: rounds_won is now part of instance state and properly reset
        self.rounds_won = {"player1": 0, "player2": 0}
        self.ai_difficulty = CONFIG["ai_difficulty"]
        self.current_opponent = None
        self.current_opponent_name = "Cyber Runner"
        self.current_dialog_index = 0
        self.dialog_timer = 0
        self.dialog_duration = 3000
        self.opponents_defeated = []
        # AI special skill state
        self.fake_balls = []
        self.flash_effect = None
        self.overclock_ball_scale = None
        self.speed_x_ref = None
        # Shop / koen
        self.koen_earned_this_match = 0
        self.shop_message = ""       # feedback text shown in shop
        self.shop_message_timer = 0
        self.shop_cursor = 0         # which item is highlighted

    def reset_ball(self, winner_side):
        ball.reset_position()
        global speed_x, speed_y
        speed_x = CONFIG["initial_ball_speed"] * (1 if winner_side == "left" else -1)
        speed_y = CONFIG["initial_ball_speed"] * random.choice([-0.8, -0.4, 0.4, 0.8])
        self.combo_counter = 0

    def update_score(self, player):
        if player == 1:
            self.player1_score += 1
        else:
            self.player2_score += 1

        self.current_rally = 0

        if self.player1_score >= 11:
            self.rounds_won["player1"] += 1
            self.reset_round()
            if self.rounds_won["player1"] > self.best_of // 2:
                self.end_game("player1")
        elif self.player2_score >= 11:
            self.rounds_won["player2"] += 1
            self.reset_round()
            if self.rounds_won["player2"] > self.best_of // 2:
                self.end_game("player2")

    def reset_round(self):
        self.player1_score = 0
        self.player2_score = 0
        self.combo_counter = 0
        self.fake_balls.clear()
        ball.reset_position()

    def full_reset(self):
        """
        BUG FIX #2: Full reset including rounds_won for rematch scenarios.
        Called when player retries after a loss.
        """
        self.player1_score = 0
        self.player2_score = 0
        self.rounds_won = {"player1": 0, "player2": 0}
        self.combo_counter = 0
        self.longest_rally = 0
        self.current_rally = 0
        self.game_over = False
        self.winner = None
        self.fake_balls = []
        self.flash_effect = None
        self.overclock_ball_scale = None
        ball.reset_position()

    def end_game(self, winner):
        self.state = GameState.GAME_OVER
        self.game_over = True
        self.winner = winner
        if winner == "player1" and self.single_player:
            self.opponents_defeated.append(self.current_opponent)
            # Award koen
            diff = self.ai_difficulty
            reward_cfg = KOEN_REWARDS.get(diff, KOEN_REWARDS["easy"])
            koen = reward_cfg["base"]
            koen += int(self.longest_rally * reward_cfg["rally_bonus"])
            koen += int(self.combo_counter * reward_cfg["combo_bonus"])
            self.koen_earned_this_match = koen
            save_manager.earn_koen(koen)

    def update_rally(self):
        self.current_rally += 1
        if self.current_rally > self.longest_rally:
            self.longest_rally = self.current_rally


class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.volume = 0.7
        try:
            self.sounds["paddle_hit"] = pygame.mixer.Sound("paddle_hit.wav")
            self.sounds["wall_hit"] = pygame.mixer.Sound("wall_hit.wav")
            self.sounds["score"] = pygame.mixer.Sound("score.wav")
            self.sounds["win"] = pygame.mixer.Sound("win.wav")
            self.sounds["skill_activate"] = pygame.mixer.Sound("skill_activate.wav")
        except:
            pass

    def play_sound(self, sound_name):
        if sound_name in self.sounds:
            self.sounds[sound_name].play()


def toggle_fullscreen():
    global window
    CONFIG["fullscreen"] = not CONFIG["fullscreen"]
    if CONFIG["fullscreen"]:
        window = display.set_mode((CONFIG["win_width"], CONFIG["win_height"]), FULLSCREEN)
        display.set_caption("Pong Champions League - A Story of Glory [FULLSCREEN]")
    else:
        window = display.set_mode((CONFIG["win_width"], CONFIG["win_height"]))
        display.set_caption("Pong Champions League - A Story of Glory")


# ── Drawing Functions ──────────────────────────────────────────────────────────

def draw_main_menu():
    window.fill((30, 30, 60))
    for i in range(CONFIG["win_height"]):
        color_val = int(30 + (i / CONFIG["win_height"]) * 50)
        pygame.draw.line(window, (color_val, color_val, 100), (0, i), (CONFIG["win_width"], i))

    title_font = font.Font(None, 70)
    option_font = font.Font(None, 40)
    hint_font = font.Font(None, 25)

    title = title_font.render("PONG GAME", True, (255, 200, 0))
    window.blit(title, (CONFIG["win_width"] // 2 - title.get_width() // 2, 50))

    option1 = option_font.render("1. Story Mode (vs AI)", True, (100, 200, 255))
    option2 = option_font.render("2. Multiplayer (2 Players)", True, (255, 100, 100))
    option3 = option_font.render("S. Skill Shop", True, (255, 220, 50))
    window.blit(option1, (50, 180))
    window.blit(option2, (50, 260))
    window.blit(option3, (50, 340))

    # Koen balance
    kf = font.Font(None, 26)
    ks = kf.render(f"🪙 {save_manager.koen} Koen", True, (255, 210, 50))
    window.blit(ks, (CONFIG["win_width"] - ks.get_width() - 15, 15))

    hint = hint_font.render("Press 1 or 2 to Select", True, (150, 150, 255))
    window.blit(hint, (CONFIG["win_width"] // 2 - hint.get_width() // 2, CONFIG["win_height"] - 60))
    fullscreen_hint = hint_font.render("Press F to Toggle Fullscreen", True, (150, 255, 150))
    window.blit(fullscreen_hint, (CONFIG["win_width"] // 2 - fullscreen_hint.get_width() // 2, CONFIG["win_height"] - 30))


def draw_intro():
    window.fill((30, 30, 60))
    for i in range(CONFIG["win_height"]):
        color_val = int(30 + (i / CONFIG["win_height"]) * 50)
        pygame.draw.line(window, (color_val, color_val, 100), (0, i), (CONFIG["win_width"], i))

    title_font = font.Font(None, 70)
    subtitle_font = font.Font(None, 40)
    text_font = font.Font(None, 28)
    hint_font = font.Font(None, 25)

    story_data = STORY["intro"]
    title = title_font.render(story_data["title"], True, (255, 200, 0))
    subtitle = subtitle_font.render(story_data["subtitle"], True, (100, 200, 255))
    window.blit(title, (CONFIG["win_width"] // 2 - title.get_width() // 2, 30))
    window.blit(subtitle, (CONFIG["win_width"] // 2 - subtitle.get_width() // 2, 110))

    y_offset = 180
    for line in story_data["text"]:
        text_surface = text_font.render(line, True, (220, 220, 220))
        window.blit(text_surface, (CONFIG["win_width"] // 2 - text_surface.get_width() // 2, y_offset))
        y_offset += 35

    hint = hint_font.render("Press SPACE to Continue", True, (150, 150, 255))
    window.blit(hint, (CONFIG["win_width"] // 2 - hint.get_width() // 2, CONFIG["win_height"] - 60))
    fullscreen_hint = hint_font.render("Press F to Toggle Fullscreen", True, (150, 255, 150))
    window.blit(fullscreen_hint, (CONFIG["win_width"] // 2 - fullscreen_hint.get_width() // 2, CONFIG["win_height"] - 30))


def draw_character_select():
    window.fill((40, 40, 80))
    title_font = font.Font(None, 60)
    option_font = font.Font(None, 35)
    desc_font = font.Font(None, 24)
    hint_font = font.Font(None, 22)

    title = title_font.render("Choose Your Opponent", True, (255, 200, 0))
    window.blit(title, (CONFIG["win_width"] // 2 - title.get_width() // 2, 20))

    opponents = STORY["character_select"]["opponents"]
    y_offset = 100
    for k in ["1", "2", "3"]:
        opp = opponents[k]
        name_text = option_font.render(f"{k}. {opp['name']}", True, opp["color"])
        desc_text = desc_font.render(opp['description'], True, (200, 200, 200))
        window.blit(name_text, (50, y_offset))
        window.blit(desc_text, (70, y_offset + 35))
        y_offset += 100

    hint = hint_font.render("Press 1, 2, or 3 to select difficulty", True, (150, 150, 255))
    window.blit(hint, (CONFIG["win_width"] // 2 - hint.get_width() // 2, CONFIG["win_height"] - 60))
    fullscreen_hint = hint_font.render("Press F to Toggle Fullscreen", True, (150, 255, 150))
    window.blit(fullscreen_hint, (CONFIG["win_width"] // 2 - fullscreen_hint.get_width() // 2, CONFIG["win_height"] - 30))


def draw_pre_match_dialog():
    window.fill((20, 20, 50))
    for i in range(CONFIG["win_height"]):
        color_val = int(20 + (i / CONFIG["win_height"]) * 40)
        pygame.draw.line(window, (color_val, color_val, 80), (0, i), (CONFIG["win_width"], i))

    opponent_font = font.Font(None, 50)
    dialog_font = font.Font(None, 32)
    hint_font = font.Font(None, 22)

    opponent_name = opponent_font.render(game_manager.current_opponent_name, True, (255, 100, 100))
    window.blit(opponent_name, (CONFIG["win_width"] // 2 - opponent_name.get_width() // 2, 80))

    dialog_box = pygame.Surface((CONFIG["win_width"] - 40, 200))
    dialog_box.fill((60, 60, 100))
    pygame.draw.rect(dialog_box, (200, 150, 50), dialog_box.get_rect(), 3)
    window.blit(dialog_box, (20, 200))

    dialogs = STORY["opponent_dialogs"][game_manager.ai_difficulty]
    current_dialog = dialogs[game_manager.current_dialog_index % len(dialogs)]

    words = current_dialog.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word
        test_surface = dialog_font.render(test_line, True, (220, 220, 220))
        if test_surface.get_width() < CONFIG["win_width"] - 80:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    y_offset = 230
    for line in lines:
        line_surface = dialog_font.render(line, True, (220, 220, 220))
        window.blit(line_surface, (40, y_offset))
        y_offset += 40

    hint = hint_font.render("Press SPACE to Start Battle!", True, (150, 255, 150))
    window.blit(hint, (CONFIG["win_width"] // 2 - hint.get_width() // 2, CONFIG["win_height"] - 60))
    fullscreen_hint = hint_font.render("Press F to Toggle Fullscreen", True, (150, 255, 150))
    window.blit(fullscreen_hint, (CONFIG["win_width"] // 2 - fullscreen_hint.get_width() // 2, CONFIG["win_height"] - 30))


def draw_pause_menu():
    pause_font = font.Font(None, 50)
    info_font = font.Font(None, 35)
    hint_font = font.Font(None, 25)

    overlay = pygame.Surface((CONFIG["win_width"], CONFIG["win_height"]))
    overlay.set_alpha(128)
    overlay.fill((0, 0, 0))
    window.blit(overlay, (0, 0))

    pause_text = pause_font.render("PAUSED", True, (255, 255, 255))
    resume_text = info_font.render("Press ESC to Resume", True, (255, 255, 255))
    menu_text = hint_font.render("Press M to Return to Menu", True, (255, 200, 100))
    fullscreen_text = hint_font.render("Press F to Toggle Fullscreen", True, (150, 255, 150))

    window.blit(pause_text, (CONFIG["win_width"] // 2 - pause_text.get_width() // 2, 100))
    window.blit(resume_text, (CONFIG["win_width"] // 2 - resume_text.get_width() // 2, 200))
    window.blit(menu_text, (CONFIG["win_width"] // 2 - menu_text.get_width() // 2, 270))
    window.blit(fullscreen_text, (CONFIG["win_width"] // 2 - fullscreen_text.get_width() // 2, 320))


def draw_skill_hud(player, x_pos, is_left=True):
    """
    Visual skill indicator with:
    - Colored icon box per skill
    - Arc sweep showing cooldown progress (like MOBA ability icons)
    - Countdown seconds in the center when on cooldown
    - Pulsing glow border when READY
    - Key label below the icon
    """
    import math

    ICON_SIZE  = 36      # square icon side length
    ICON_GAP   = 8       # gap between icons
    ARC_WIDTH  = 4       # thickness of cooldown arc
    START_ANGLE = math.pi / 2   # arc starts from top (12 o'clock)

    key_font      = font.Font(None, 15)
    cd_font       = font.Font(None, 20)
    name_font     = font.Font(None, 14)

    # Layout: icons stacked vertically starting at y=50
    y_start = 50

    for i, skill_name in enumerate(player.available_skills):
        skill_config = SKILLS_CONFIG[skill_name]
        base_color   = skill_config["color"]
        key_label    = pygame.key.name(skill_config["key"]).upper()
        is_ready     = player.skill_ready[skill_name]
        is_active    = skill_name in player.active_skills

        ix = x_pos
        iy = y_start + i * (ICON_SIZE + ICON_GAP + 14)   # +14 for key label below
        cx = ix + ICON_SIZE // 2
        cy = iy + ICON_SIZE // 2
        radius = ICON_SIZE // 2

        # ── Icon background ────────────────────────────────────────────
        if is_ready:
            # Bright background
            bg_color = tuple(min(255, int(c * 0.35)) for c in base_color)
        elif is_active:
            # Active: slightly glowing teal tint
            bg_color = (20, 60, 50)
        else:
            # On cooldown: dark grey
            bg_color = (30, 30, 30)

        pygame.draw.rect(window, bg_color, (ix, iy, ICON_SIZE, ICON_SIZE), border_radius=6)

        # ── Border ─────────────────────────────────────────────────────
        if is_ready:
            # Pulsing border: oscillate alpha via brightness using time
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.004 + i))
            border_color = tuple(int(c * (0.6 + 0.4 * pulse)) for c in base_color)
            pygame.draw.rect(window, border_color, (ix, iy, ICON_SIZE, ICON_SIZE), width=2, border_radius=6)
        elif is_active:
            pygame.draw.rect(window, (100, 255, 200), (ix, iy, ICON_SIZE, ICON_SIZE), width=2, border_radius=6)
        else:
            pygame.draw.rect(window, (80, 80, 80), (ix, iy, ICON_SIZE, ICON_SIZE), width=1, border_radius=6)

        # ── Cooldown arc sweep ─────────────────────────────────────────
        if not is_ready and not is_active:
            cooldown_frames  = player.skill_cooldowns[skill_name]
            max_frames       = SKILLS_CONFIG[skill_name]["cooldown"]
            progress         = cooldown_frames / max_frames   # 1.0 = just used, 0.0 = ready

            # Dark overlay on icon while on cooldown
            overlay = pygame.Surface((ICON_SIZE, ICON_SIZE), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            window.blit(overlay, (ix, iy))

            # Draw arc (remaining cooldown portion) — clock-wise sweep from top
            arc_rect = pygame.Rect(ix + ARC_WIDTH, iy + ARC_WIDTH,
                                   ICON_SIZE - ARC_WIDTH * 2, ICON_SIZE - ARC_WIDTH * 2)
            # pygame.draw.arc goes counter-clockwise in screen coords
            # We want a clock-wise sweep showing how much is LEFT (progress)
            end_angle   = START_ANGLE
            start_angle = START_ANGLE + (2 * math.pi * progress)
            if progress > 0.01:
                try:
                    pygame.draw.arc(window, (220, 80, 40), arc_rect,
                                    end_angle, start_angle, ARC_WIDTH)
                except Exception:
                    pass

            # Countdown seconds in the centre
            secs_left = max(1, (cooldown_frames + FPS - 1) // FPS)
            cd_surf = cd_font.render(str(secs_left), True, (255, 255, 255))
            window.blit(cd_surf, (cx - cd_surf.get_width() // 2,
                                  cy - cd_surf.get_height() // 2))

        elif is_active:
            # Show remaining active duration as a green arc
            duration_frames = player.active_skills[skill_name]
            max_duration    = SKILLS_CONFIG[skill_name]["duration"]
            progress        = duration_frames / max_duration  # 1.0 = just activated

            arc_rect = pygame.Rect(ix + ARC_WIDTH, iy + ARC_WIDTH,
                                   ICON_SIZE - ARC_WIDTH * 2, ICON_SIZE - ARC_WIDTH * 2)
            end_angle   = START_ANGLE
            start_angle = START_ANGLE + (2 * math.pi * progress)
            if progress > 0.01:
                try:
                    pygame.draw.arc(window, (100, 255, 180), arc_rect,
                                    end_angle, start_angle, ARC_WIDTH)
                except Exception:
                    pass

            # Show remaining seconds
            secs_left = max(1, (duration_frames + FPS - 1) // FPS)
            cd_surf = cd_font.render(str(secs_left), True, (100, 255, 180))
            window.blit(cd_surf, (cx - cd_surf.get_width() // 2,
                                  cy - cd_surf.get_height() // 2))

        else:
            # READY: show skill initial letter in the centre
            letter = skill_config["name"][0]
            letter_surf = cd_font.render(letter, True, base_color)
            window.blit(letter_surf, (cx - letter_surf.get_width() // 2,
                                      cy - letter_surf.get_height() // 2))

        # ── Key label below icon ────────────────────────────────────────
        key_color = base_color if is_ready else (100, 100, 100)
        key_surf  = key_font.render(f"[{key_label}]", True, key_color)
        window.blit(key_surf, (cx - key_surf.get_width() // 2, iy + ICON_SIZE + 2))


def draw_ai_special_hud():
    """
    Draw AI special skill indicators on the right side of the screen,
    below the normal skill HUD. Shows icon, name, and cooldown arc.
    Only shown during Story Mode (vs AI).
    """
    if not game_manager.single_player:
        return

    import math
    my_specials = racket2.ai_special_skills.get(racket2.ai_difficulty, [])
    if not my_specials:
        return

    ICON_SIZE = 36
    ICON_GAP  = 8
    ARC_WIDTH = 4
    START_ANGLE = math.pi / 2

    cd_font  = font.Font(None, 20)
    lbl_font = font.Font(None, 14)

    # Position below the normal 3-skill HUD on the right
    x_pos   = CONFIG["win_width"] - 140
    y_start = 50 + 3 * (ICON_SIZE + ICON_GAP + 14) + 16  # after 3 normal icons

    title_font = font.Font(None, 15)
    title_surf = title_font.render("SPECIAL", True, (220, 180, 255))
    window.blit(title_surf, (x_pos, y_start - 14))

    for i, skill_name in enumerate(my_specials):
        cfg = AI_SKILLS_CONFIG[skill_name]
        base_color = cfg["color"]
        is_ready   = racket2.ai_special_ready[skill_name]
        is_active  = skill_name in racket2.ai_special_active

        ix = x_pos
        iy = y_start + i * (ICON_SIZE + ICON_GAP + 14)
        cx = ix + ICON_SIZE // 2
        cy = iy + ICON_SIZE // 2

        # Background
        if is_ready:
            bg = tuple(min(255, int(c * 0.3)) for c in base_color)
        else:
            bg = (25, 25, 25)
        pygame.draw.rect(window, bg, (ix, iy, ICON_SIZE, ICON_SIZE), border_radius=6)

        # Border
        if is_ready:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.004 + i + 10))
            bc = tuple(int(c * (0.5 + 0.5 * pulse)) for c in base_color)
            pygame.draw.rect(window, bc, (ix, iy, ICON_SIZE, ICON_SIZE), width=2, border_radius=6)
        elif is_active:
            pygame.draw.rect(window, (220, 150, 255), (ix, iy, ICON_SIZE, ICON_SIZE), width=2, border_radius=6)
        else:
            pygame.draw.rect(window, (70, 70, 70), (ix, iy, ICON_SIZE, ICON_SIZE), width=1, border_radius=6)

        # Cooldown arc + number
        if not is_ready and not is_active:
            overlay = pygame.Surface((ICON_SIZE, ICON_SIZE), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            window.blit(overlay, (ix, iy))

            frames   = racket2.ai_special_cooldowns[skill_name]
            max_cd   = cfg["cooldown"]
            progress = frames / max_cd
            arc_rect = pygame.Rect(ix + ARC_WIDTH, iy + ARC_WIDTH,
                                   ICON_SIZE - ARC_WIDTH * 2, ICON_SIZE - ARC_WIDTH * 2)
            if progress > 0.01:
                try:
                    pygame.draw.arc(window, (200, 60, 255), arc_rect,
                                    START_ANGLE, START_ANGLE + 2 * math.pi * progress, ARC_WIDTH)
                except Exception:
                    pass
            secs = max(1, (frames + FPS - 1) // FPS)
            ns = cd_font.render(str(secs), True, (255, 255, 255))
            window.blit(ns, (cx - ns.get_width() // 2, cy - ns.get_height() // 2))

        elif is_active:
            dur_frames = racket2.ai_special_active[skill_name]
            max_dur    = cfg["duration"]
            progress   = dur_frames / max_dur
            arc_rect   = pygame.Rect(ix + ARC_WIDTH, iy + ARC_WIDTH,
                                     ICON_SIZE - ARC_WIDTH * 2, ICON_SIZE - ARC_WIDTH * 2)
            if progress > 0.01:
                try:
                    pygame.draw.arc(window, (220, 150, 255), arc_rect,
                                    START_ANGLE, START_ANGLE + 2 * math.pi * progress, ARC_WIDTH)
                except Exception:
                    pass
            secs = max(1, (dur_frames + FPS - 1) // FPS)
            ns = cd_font.render(str(secs), True, (220, 150, 255))
            window.blit(ns, (cx - ns.get_width() // 2, cy - ns.get_height() // 2))
        else:
            letter = cfg["name"][0]
            ls = cd_font.render(letter, True, base_color)
            window.blit(ls, (cx - ls.get_width() // 2, cy - ls.get_height() // 2))

        # Skill name label
        short_name = cfg["name"].split()[0]  # e.g. "Glitch", "Overclock", "Phase", "Phantom"
        lbl = lbl_font.render(short_name, True, base_color if is_ready else (90, 90, 90))
        window.blit(lbl, (cx - lbl.get_width() // 2, iy + ICON_SIZE + 2))


def draw_shop():
    """Draw the shop screen with purchasable skills."""
    window.fill((10, 15, 35))
    # Gradient background
    for i in range(CONFIG["win_height"]):
        v = int(10 + (i / CONFIG["win_height"]) * 30)
        pygame.draw.line(window, (v, v, int(v * 1.8)), (0, i), (CONFIG["win_width"], i))

    title_font  = font.Font(None, 55)
    price_font  = font.Font(None, 28)
    desc_font   = font.Font(None, 22)
    hint_font   = font.Font(None, 20)
    koen_font   = font.Font(None, 32)

    # Title
    title = title_font.render("⚡ SKILL SHOP ⚡", True, (255, 220, 50))
    window.blit(title, (CONFIG["win_width"] // 2 - title.get_width() // 2, 15))

    # Koen balance
    koen_surf = koen_font.render(f"🪙 {save_manager.koen} Koen", True, (255, 200, 50))
    window.blit(koen_surf, (CONFIG["win_width"] // 2 - koen_surf.get_width() // 2, 65))

    items = list(SHOP_ITEMS.items())
    card_w, card_h = 520, 90
    card_x = (CONFIG["win_width"] - card_w) // 2

    for i, (skill_key, item) in enumerate(items):
        card_y = 110 + i * (card_h + 12)
        owned   = skill_key in save_manager.owned_skills
        selected = (game_manager.shop_cursor == i)
        can_buy = save_manager.koen >= item["price"] and not owned

        # Card background
        if owned:
            bg = (20, 50, 30)
            border = (60, 180, 80)
        elif selected:
            bg = (30, 30, 60)
            border = item["color"]
        else:
            bg = (20, 20, 40)
            border = (60, 60, 100)

        pygame.draw.rect(window, bg, (card_x, card_y, card_w, card_h), border_radius=10)
        bw = 3 if selected else 1
        pygame.draw.rect(window, border, (card_x, card_y, card_w, card_h), width=bw, border_radius=10)

        # Icon circle
        ic = item["color"]
        pygame.draw.circle(window, ic, (card_x + 40, card_y + card_h // 2), 24)
        icon_font = font.Font(None, 32)
        icon_surf = icon_font.render(item["icon"], True, (0, 0, 0))
        window.blit(icon_surf, (card_x + 40 - icon_surf.get_width() // 2,
                                 card_y + card_h // 2 - icon_surf.get_height() // 2))

        # Name + key hint
        name_col = (100, 255, 120) if owned else (item["color"] if selected else (200, 200, 200))
        name_surf = price_font.render(item["name"], True, name_col)
        window.blit(name_surf, (card_x + 75, card_y + 12))

        key_label = pygame.key.name(item["key"]).upper()
        key_surf = hint_font.render(f"[{key_label}] in-game", True, (120, 120, 160))
        window.blit(key_surf, (card_x + 75, card_y + 38))

        desc_surf = desc_font.render(item["description"], True, (160, 160, 180))
        window.blit(desc_surf, (card_x + 75, card_y + 60))

        # Price / status
        if owned:
            status = price_font.render("✓ OWNED", True, (80, 220, 100))
        elif can_buy:
            status = price_font.render(f"🪙 {item['price']}", True, (255, 220, 50))
        else:
            status = price_font.render(f"🪙 {item['price']}", True, (150, 80, 80))
        window.blit(status, (card_x + card_w - status.get_width() - 15, card_y + card_h // 2 - status.get_height() // 2))

    # Shop message (buy feedback)
    if game_manager.shop_message and game_manager.shop_message_timer > 0:
        msg_col = (100, 255, 100) if "Bought" in game_manager.shop_message else (255, 100, 100)
        msg_surf = price_font.render(game_manager.shop_message, True, msg_col)
        window.blit(msg_surf, (CONFIG["win_width"] // 2 - msg_surf.get_width() // 2, 420))

    # Controls hint
    hints = [
        "↑/↓ Navigate    ENTER Buy    ESC Back to Menu",
    ]
    for hi, h in enumerate(hints):
        hs = hint_font.render(h, True, (100, 100, 150))
        window.blit(hs, (CONFIG["win_width"] // 2 - hs.get_width() // 2, CONFIG["win_height"] - 30 + hi * 18))


def draw_shop_skill_hud():
    """Draw purchased shop skill icons below regular skill HUD during gameplay."""
    if not game_manager.single_player:
        return
    owned = save_manager.owned_skills
    if not owned:
        return

    import math
    ICON_SIZE = 32
    ICON_GAP  = 6
    ARC_WIDTH = 3
    START_ANGLE = math.pi / 2
    cd_font  = font.Font(None, 18)
    lbl_font = font.Font(None, 13)

    # Position below player 1's normal HUD (left side)
    x_pos   = 10
    y_start = 50 + 3 * (36 + 8 + 14) + 20

    title_f = font.Font(None, 14)
    ts = title_f.render("SHOP SKILLS", True, (255, 220, 50))
    window.blit(ts, (x_pos, y_start - 13))

    for i, skill_key in enumerate(owned):
        item     = SHOP_ITEMS[skill_key]
        is_ready = racket1.shop_skill_ready[skill_key]
        is_active = skill_key in racket1.shop_skill_active

        ix = x_pos + i * (ICON_SIZE + ICON_GAP)
        iy = y_start
        cx = ix + ICON_SIZE // 2
        cy = iy + ICON_SIZE // 2

        bg = tuple(min(255, int(c * 0.3)) for c in item["color"]) if is_ready else (25, 25, 25)
        pygame.draw.rect(window, bg, (ix, iy, ICON_SIZE, ICON_SIZE), border_radius=5)

        if is_ready:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.004 + i))
            bc = tuple(int(c * (0.5 + 0.5 * pulse)) for c in item["color"])
            pygame.draw.rect(window, bc, (ix, iy, ICON_SIZE, ICON_SIZE), width=2, border_radius=5)
        elif is_active:
            pygame.draw.rect(window, (255, 255, 150), (ix, iy, ICON_SIZE, ICON_SIZE), width=2, border_radius=5)
        else:
            pygame.draw.rect(window, (60, 60, 60), (ix, iy, ICON_SIZE, ICON_SIZE), width=1, border_radius=5)

        if not is_ready and not is_active:
            overlay = pygame.Surface((ICON_SIZE, ICON_SIZE), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            window.blit(overlay, (ix, iy))
            frames   = racket1.shop_skill_cooldowns[skill_key]
            max_cd   = item["cooldown"]
            progress = frames / max_cd if max_cd else 0
            arc_rect = pygame.Rect(ix + ARC_WIDTH, iy + ARC_WIDTH,
                                   ICON_SIZE - ARC_WIDTH * 2, ICON_SIZE - ARC_WIDTH * 2)
            if progress > 0.01:
                try:
                    pygame.draw.arc(window, item["color"], arc_rect,
                                    START_ANGLE, START_ANGLE + 2 * math.pi * progress, ARC_WIDTH)
                except Exception:
                    pass
            secs = max(1, (frames + FPS - 1) // FPS)
            ns = cd_font.render(str(secs), True, (255, 255, 255))
            window.blit(ns, (cx - ns.get_width() // 2, cy - ns.get_height() // 2))
        else:
            ls = cd_font.render(item["icon"], True, item["color"] if is_ready else (255, 255, 150))
            window.blit(ls, (cx - ls.get_width() // 2, cy - ls.get_height() // 2))

        # Key label
        key_label = pygame.key.name(item["key"]).upper()
        kl = lbl_font.render(f"[{key_label}]", True, item["color"] if is_ready else (80, 80, 80))
        window.blit(kl, (cx - kl.get_width() // 2, iy + ICON_SIZE + 1))


def draw_hud():
    hud_font = font.Font(None, 30)
    score_text = hud_font.render(f"{game_manager.player1_score}  :  {game_manager.player2_score}", True, (0, 0, 0))
    window.blit(score_text, (CONFIG["win_width"] // 2 - score_text.get_width() // 2, 10))

    name_font = font.Font(None, 22)
    if game_manager.multiplayer:
        opp_text = name_font.render("Player 1 vs Player 2", True, (100, 100, 100))
    else:
        opp_text = name_font.render(f"vs {game_manager.current_opponent_name}", True, (100, 100, 100))
    window.blit(opp_text, (CONFIG["win_width"] - opp_text.get_width() - 10, 10))

    for y in range(0, CONFIG["win_height"], 20):
        pygame.draw.line(window, (100, 100, 100), (CONFIG["win_width"] // 2, y), (CONFIG["win_width"] // 2, y + 10), 2)

    if game_manager.combo_counter > 0:
        combo_text = hud_font.render(f"Combo: {game_manager.combo_counter}", True, (255, 100, 0))
        window.blit(combo_text, (10, 10))

    if game_manager.current_rally > 0:
        rally_text = hud_font.render(f"Rally: {game_manager.current_rally}", True, (100, 100, 200))
        window.blit(rally_text, (CONFIG["win_width"] - rally_text.get_width() - 10, 35))

    draw_skill_hud(racket1, 10, is_left=True)
    draw_skill_hud(racket2, CONFIG["win_width"] - 140, is_left=False)

    # Koen balance (top-right corner)
    if game_manager.single_player:
        kf = font.Font(None, 22)
        ks = kf.render(f"🪙 {save_manager.koen}", True, (255, 210, 50))
        window.blit(ks, (CONFIG["win_width"] // 2 - ks.get_width() // 2, 30))

    hint_font = font.Font(None, 20)
    # BUG FIX #7: Updated multiplayer controls hint so it doesn't confuse skill keys with movement keys
    if game_manager.multiplayer:
        pause_hint = hint_font.render("P1: W/S move | P2: ↑/↓ move | ESC Pause", True, (150, 150, 150))
    else:
        pause_hint = hint_font.render("ESC to Pause | Q/E/R Skills | F Fullscreen", True, (150, 150, 150))
    window.blit(pause_hint, (10, CONFIG["win_height"] - 25))


def draw_game_over():
    window.fill((20, 20, 50))
    for i in range(CONFIG["win_height"]):
        color_val = int(20 + (i / CONFIG["win_height"]) * 40)
        pygame.draw.line(window, (color_val, color_val, 80), (0, i), (CONFIG["win_width"], i))

    title_font = font.Font(None, 60)
    text_font = font.Font(None, 35)
    stats_font = font.Font(None, 28)
    hint_font = font.Font(None, 25)

    if game_manager.winner == "player1":
        title_color = (0, 255, 0)
        title_text = "PLAYER 1 WINS!" if game_manager.multiplayer else "VICTORY!"
        dialog_text = f"You defeated {game_manager.current_opponent_name}!" if not game_manager.multiplayer else "Player 1 is the Champion!"
    else:
        title_color = (255, 0, 0)
        title_text = "PLAYER 2 WINS!" if game_manager.multiplayer else "DEFEAT"
        dialog_text = f"{game_manager.current_opponent_name} prevails!" if not game_manager.multiplayer else "Player 2 is the Champion!"

    title = title_font.render(title_text, True, title_color)
    window.blit(title, (CONFIG["win_width"] // 2 - title.get_width() // 2, 40))
    dialog = text_font.render(dialog_text, True, (220, 220, 220))
    window.blit(dialog, (CONFIG["win_width"] // 2 - dialog.get_width() // 2, 130))

    final_score = stats_font.render(
        f"Final Score: {game_manager.player1_score} - {game_manager.player2_score}",
        True, (200, 200, 100)
    )
    longest_rally_text = stats_font.render(
        f"Longest Rally: {game_manager.longest_rally} hits",
        True, (100, 200, 200)
    )
    window.blit(final_score, (CONFIG["win_width"] // 2 - final_score.get_width() // 2, 210))
    window.blit(longest_rally_text, (CONFIG["win_width"] // 2 - longest_rally_text.get_width() // 2, 260))

    # Koen earned this match
    if game_manager.single_player and game_manager.winner == "player1" and game_manager.koen_earned_this_match > 0:
        koen_font2 = font.Font(None, 30)
        ke = koen_font2.render(f"🪙 +{game_manager.koen_earned_this_match} Koen earned!  (Total: {save_manager.koen})", True, (255, 210, 50))
        window.blit(ke, (CONFIG["win_width"] // 2 - ke.get_width() // 2, 300))

    if game_manager.multiplayer or (game_manager.winner != "player1"):
        hint = hint_font.render("Press SPACE to Play Again", True, (100, 255, 100))
    elif len(game_manager.opponents_defeated) < 3:
        hint = hint_font.render("Press SPACE for Next Challenge", True, (100, 255, 100))
    else:
        hint = hint_font.render("Press SPACE to See Ending", True, (255, 200, 0))

    window.blit(hint, (CONFIG["win_width"] // 2 - hint.get_width() // 2, CONFIG["win_height"] - 60))
    menu_hint = hint_font.render("Press M to Return to Menu", True, (150, 200, 255))
    window.blit(menu_hint, (CONFIG["win_width"] // 2 - menu_hint.get_width() // 2, CONFIG["win_height"] - 30))


def draw_ending():
    window.fill((30, 30, 60))
    for i in range(CONFIG["win_height"]):
        color_val = int(30 + (i / CONFIG["win_height"]) * 50)
        pygame.draw.line(window, (color_val, color_val, 100), (0, i), (CONFIG["win_width"], i))

    title_font = font.Font(None, 70)
    text_font = font.Font(None, 28)
    hint_font = font.Font(None, 25)

    story_data = STORY["victory"]
    title = title_font.render(story_data["title"], True, (255, 200, 0))
    window.blit(title, (CONFIG["win_width"] // 2 - title.get_width() // 2, 30))

    y_offset = 130
    for line in story_data["text"]:
        text_surface = text_font.render(line, True, (220, 220, 220))
        window.blit(text_surface, (CONFIG["win_width"] // 2 - text_surface.get_width() // 2, y_offset))
        y_offset += 35

    hint = hint_font.render("Press SPACE to Return to Menu", True, (150, 150, 255))
    window.blit(hint, (CONFIG["win_width"] // 2 - hint.get_width() // 2, CONFIG["win_height"] - 60))
    fullscreen_hint = hint_font.render("Press F to Toggle Fullscreen", True, (150, 255, 150))
    window.blit(fullscreen_hint, (CONFIG["win_width"] // 2 - fullscreen_hint.get_width() // 2, CONFIG["win_height"] - 30))


def increase_ball_speed():
    """
    BUG FIX #5: Rewritten to safely scale speed without losing direction or
    producing NaN when speed_x is near zero.
    """
    global speed_x, speed_y
    if game_manager.current_rally % 5 == 0 and game_manager.current_rally > 0:
        current_speed = (speed_x ** 2 + speed_y ** 2) ** 0.5
        if current_speed == 0:
            return
        speed_multiplier = min(
            1 + (game_manager.current_rally / 50),
            CONFIG["max_ball_speed"] / CONFIG["initial_ball_speed"]
        )
        target_speed = CONFIG["initial_ball_speed"] * speed_multiplier
        if current_speed < target_speed:
            scale = target_speed / current_speed
            speed_x *= scale
            speed_y *= scale


def handle_ball_collision():
    """
    Robust swept collision detection.

    Root causes of ball sticking:
    A) At high speed the ball can move MORE than its own width in one frame,
       skipping past the thin paddle entirely — classic tunnelling.
    B) ball.rotate() calls get_rect(center=...) every frame, which can nudge
       the rect by ±1 px due to rounding.  If the ball is already overlapping
       a paddle this causes repeated direction flips that lock the ball inside.

    Fix strategy:
    1. Remember ball position BEFORE moving (done in game loop via prev_x).
    2. Check if the ball's horizontal path this frame crossed either paddle edge.
    3. If it did, snap the ball to the correct side and flip speed_x ONCE.
    4. Never flip speed_x if we're already moving away — prevents stutter-lock.
    """
    global speed_x, speed_y

    ball_rect = ball.rect

    # ── Left paddle (racket1) ──────────────────────────────────────────────
    if speed_x < 0:
        paddle_right = racket1.rect.right
        crossed = ball_prev_x <= paddle_right and ball_rect.left <= paddle_right
        if crossed and ball_rect.colliderect(racket1.rect):
            speed_x = abs(speed_x)
            ball_rect.left = paddle_right + 1
            game_manager.combo_counter += 1
            sound_manager.play_sound("paddle_hit")
            increase_ball_speed()
            racket1.on_paddle_hit_shop_skills()   # Ball Control check

    # ── Right paddle (racket2) ─────────────────────────────────────────────
    elif speed_x > 0:
        paddle_left = racket2.rect.left
        crossed = ball_prev_x >= paddle_left and ball_rect.right >= paddle_left
        if crossed and ball_rect.colliderect(racket2.rect):
            speed_x = -abs(speed_x)
            ball_rect.right = paddle_left - 1
            game_manager.combo_counter += 1
            sound_manager.play_sound("paddle_hit")
            increase_ball_speed()


# ── Initialisation ─────────────────────────────────────────────────────────────

pygame.init()
back = CONFIG["background_color"]
win_width = CONFIG["win_width"]
win_height = CONFIG["win_height"]
window = display.set_mode((win_width, win_height))
display.set_caption("Pong Champions League - A Story of Glory")
window.fill(back)

clock = time.Clock()
FPS = 60
font.init()
sound_manager = SoundManager()
save_manager = SaveManager()
game_manager = GameManager()

racket1 = Player("racket.png", 30, 200, CONFIG["paddle_speed"], CONFIG["paddle_width"], CONFIG["paddle_height"], is_ai=False)
racket2 = Player("racket.png", CONFIG["win_width"] - 80, 200, CONFIG["paddle_speed"], CONFIG["paddle_width"], CONFIG["paddle_height"], is_ai=False)
ball = Ball("tenis_ball.png", win_width // 2, win_height // 2, 0, CONFIG["ball_size"], CONFIG["ball_size"])

speed_x = CONFIG["initial_ball_speed"]
speed_y = CONFIG["initial_ball_speed"]

# ── Main Game Loop ─────────────────────────────────────────────────────────────

running = True
while running:
    for e in event.get():
        if e.type == QUIT:
            running = False
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_f or e.key == pygame.K_F11:
                toggle_fullscreen()
            elif e.key == pygame.K_m:
                if game_manager.state == GameState.PLAYING:
                    game_manager.state = GameState.PAUSED
                elif game_manager.state in (GameState.PAUSED, GameState.GAME_OVER):
                    game_manager = GameManager()
                    game_manager.state = GameState.MAIN_MENU
                    racket1.rect.y = 200
                    racket2.rect.y = 200
                    racket2.is_ai = False
            elif e.key == K_ESCAPE:
                if game_manager.state == GameState.PLAYING:
                    game_manager.state = GameState.PAUSED
                elif game_manager.state == GameState.PAUSED:
                    game_manager.state = GameState.PLAYING
            elif e.key == pygame.K_SPACE:
                if game_manager.state == GameState.INTRO:
                    game_manager.state = GameState.CHARACTER_SELECT
                elif game_manager.state == GameState.PRE_MATCH:
                    game_manager.state = GameState.PLAYING
                elif game_manager.state == GameState.GAME_OVER:
                    if game_manager.multiplayer:
                        # BUG FIX #2: use full_reset so rounds_won is cleared too
                        game_manager.full_reset()
                        game_manager.state = GameState.PLAYING
                        racket1.rect.y = 200
                        racket2.rect.y = 200
                    elif game_manager.winner == "player1":
                        if len(game_manager.opponents_defeated) < 3:
                            game_manager.state = GameState.CHARACTER_SELECT
                        else:
                            game_manager.state = GameState.ENDING
                    else:
                        # BUG FIX #2: full reset on retry after defeat
                        game_manager.full_reset()
                        game_manager.state = GameState.PRE_MATCH
                        racket1.rect.y = 200
                        racket2.rect.y = 200
                elif game_manager.state == GameState.ENDING:
                    game_manager = GameManager()
                    game_manager.state = GameState.MAIN_MENU
                    racket2.is_ai = False
            elif e.key == pygame.K_s and game_manager.state == GameState.MAIN_MENU:
                game_manager.state = GameState.SHOP
                game_manager.shop_cursor = 0
                game_manager.shop_message = ""
            # Shop navigation
            elif game_manager.state == GameState.SHOP:
                items = list(SHOP_ITEMS.keys())
                if e.key == K_ESCAPE:
                    game_manager.state = GameState.MAIN_MENU
                elif e.key == K_UP:
                    game_manager.shop_cursor = (game_manager.shop_cursor - 1) % len(items)
                elif e.key == K_DOWN:
                    game_manager.shop_cursor = (game_manager.shop_cursor + 1) % len(items)
                elif e.key == pygame.K_RETURN:
                    chosen_key = items[game_manager.shop_cursor]
                    ok, msg = save_manager.buy(chosen_key)
                    game_manager.shop_message = msg
                    game_manager.shop_message_timer = 120
            elif e.key == pygame.K_1 and game_manager.state == GameState.MAIN_MENU:
                game_manager = GameManager(single_player=True)
                game_manager.state = GameState.INTRO
                racket2.is_ai = True
            elif e.key == pygame.K_2 and game_manager.state == GameState.MAIN_MENU:
                game_manager = GameManager(multiplayer=True)
                game_manager.state = GameState.PLAYING
                racket2.is_ai = False
            elif e.key == pygame.K_1 and game_manager.state == GameState.CHARACTER_SELECT:
                game_manager.ai_difficulty = "easy"
                game_manager.current_opponent = "easy"
                game_manager.current_opponent_name = "Circuit Bot"
                CONFIG["ai_difficulty"] = "easy"
                racket2.ai_difficulty = "easy"
                game_manager.state = GameState.PRE_MATCH
                game_manager.current_dialog_index = 0
                racket2.is_ai = True
            elif e.key == pygame.K_2 and game_manager.state == GameState.CHARACTER_SELECT:
                game_manager.ai_difficulty = "medium"
                game_manager.current_opponent = "medium"
                game_manager.current_opponent_name = "Cyber Runner"
                CONFIG["ai_difficulty"] = "medium"
                racket2.ai_difficulty = "medium"
                game_manager.state = GameState.PRE_MATCH
                game_manager.current_dialog_index = 0
                racket2.is_ai = True
            elif e.key == pygame.K_3 and game_manager.state == GameState.CHARACTER_SELECT:
                game_manager.ai_difficulty = "hard"
                game_manager.current_opponent = "hard"
                game_manager.current_opponent_name = "Shadow Master"
                CONFIG["ai_difficulty"] = "hard"
                racket2.ai_difficulty = "hard"
                game_manager.state = GameState.PRE_MATCH
                game_manager.current_dialog_index = 0
                racket2.is_ai = True
            elif e.key == K_q and game_manager.state == GameState.PLAYING and not game_manager.multiplayer:
                racket1.use_skill("speed_boost")
            elif e.key == K_e and game_manager.state == GameState.PLAYING and not game_manager.multiplayer:
                racket1.use_skill("paddle_grow")
            elif e.key == pygame.K_r and game_manager.state == GameState.PLAYING and not game_manager.multiplayer:
                racket1.use_skill("shield")
            # Shop skills (Z, X, C)
            elif e.key == pygame.K_z and game_manager.state == GameState.PLAYING and not game_manager.multiplayer:
                racket1.use_shop_skill("ball_control")
            elif e.key == pygame.K_x and game_manager.state == GameState.PLAYING and not game_manager.multiplayer:
                racket1.use_shop_skill("time_slow")
            elif e.key == pygame.K_c and game_manager.state == GameState.PLAYING and not game_manager.multiplayer:
                racket1.use_shop_skill("shooting_star")
            # BUG FIX #7: Multiplayer skill keys changed to avoid conflict with movement
            # Player 2 skill keys: RCTRL=speed_boost, RSHIFT=paddle_grow, END=shield
            elif e.key == pygame.K_RCTRL and game_manager.state == GameState.PLAYING and game_manager.multiplayer:
                racket2.use_skill("speed_boost")
            elif e.key == pygame.K_RSHIFT and game_manager.state == GameState.PLAYING and game_manager.multiplayer:
                racket2.use_skill("paddle_grow")
            elif e.key == pygame.K_END and game_manager.state == GameState.PLAYING and game_manager.multiplayer:
                racket2.use_skill("shield")

    # ── State Machine ────────────────────────────────────────────────────────

    if game_manager.state == GameState.MAIN_MENU:
        draw_main_menu()
    elif game_manager.state == GameState.SHOP:
        if game_manager.shop_message_timer > 0:
            game_manager.shop_message_timer -= 1
        draw_shop()
    elif game_manager.state == GameState.INTRO:
        draw_intro()
    elif game_manager.state == GameState.CHARACTER_SELECT:
        draw_character_select()
    elif game_manager.state == GameState.PRE_MATCH:
        draw_pre_match_dialog()
    elif game_manager.state == GameState.PAUSED:
        draw_pause_menu()
    elif game_manager.state == GameState.GAME_OVER:
        draw_game_over()
    elif game_manager.state == GameState.ENDING:
        draw_ending()
    elif game_manager.state == GameState.PLAYING:
        window.fill(back)
        racket1.update_l()

        # Pass current ball direction so AI special skill logic can read it
        game_manager.speed_x_ref = speed_x

        racket2.update_r(game_manager)
        racket1.update_skills()
        racket2.update_skills()

        ball_prev_x = ball.rect.centerx   # save BEFORE moving — used by swept collision

        # Time Slow — halve ball speed this frame
        slow = 0.5 if racket1.time_slow_active else 1.0
        ball.rect.x += int(speed_x * slow)
        ball.rect.y += int(speed_y * slow)

        ball.update_trail()
        ball.rotate(speed_x, speed_y)
        game_manager.update_rally()

        handle_ball_collision()

        # Wall collision
        if ball.rect.y > win_height - 50 or ball.rect.y < 0:
            sound_manager.play_sound("wall_hit")
            speed_y *= -1

        # Left side miss → Player 2 scores
        if ball.rect.x < 0:
            sound_manager.play_sound("score")
            if racket1.use_shield():
                ball.reset_position()
                speed_x = CONFIG["initial_ball_speed"]
                speed_y = CONFIG["initial_ball_speed"] * random.choice([-0.8, -0.4, 0.4, 0.8])
            else:
                game_manager.update_score(2)
                game_manager.reset_ball("right")
                # Undo overclock ball speed boost if active
                if game_manager.overclock_ball_scale:
                    game_manager.overclock_ball_scale = None

        # Right side miss → Player 1 scores
        if ball.rect.x > win_width:
            sound_manager.play_sound("score")
            if racket2.use_shield():
                ball.reset_position()
                speed_x = -CONFIG["initial_ball_speed"]
                speed_y = CONFIG["initial_ball_speed"] * random.choice([-0.8, -0.4, 0.4, 0.8])
            else:
                game_manager.update_score(1)
                game_manager.reset_ball("left")
                if game_manager.overclock_ball_scale:
                    game_manager.overclock_ball_scale = None

        # ── Fake balls (Phantom Ball skill) ───────────────────────────
        for fb in game_manager.fake_balls[:]:
            fb.update()
            fb.draw()
            if not fb.alive:
                game_manager.fake_balls.remove(fb)

        ball.draw_trail()
        racket1.reset()
        racket2.reset()
        ball.reset()

        # ── Flash effect (skill activation screen flash) ──────────────
        if game_manager.flash_effect:
            fe = game_manager.flash_effect
            flash_surf = pygame.Surface((win_width, win_height), pygame.SRCALPHA)
            alpha = int(180 * (fe["timer"] / 12))
            flash_surf.fill((*fe["color"], alpha))
            window.blit(flash_surf, (0, 0))
            fe["timer"] -= 1
            if fe["timer"] <= 0:
                game_manager.flash_effect = None

        draw_hud()
        draw_shop_skill_hud()
        draw_ai_special_hud()

    display.update()
    clock.tick(FPS)

pygame.quit()
