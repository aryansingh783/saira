import pygame
import socket
import json
import threading
import time
import random
import math
from dataclasses import dataclass
from typing import Optional, Tuple, List
from enum import Enum

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

class FaceState(Enum):
    """Face states"""
    IDLE = "IDLE"
    TALKING = "TALKING"
    LISTENING = "LISTENING"
    THINKING = "THINKING"

@dataclass
class DisplayConfig:
    """Display settings"""
    fullscreen_width: int = 2340
    fullscreen_height: int = 1080
    start_width: int = 1280
    start_height: int = 720
    target_fps: int = 60

@dataclass
class ColorScheme:
    """Modern color palette"""
    background: Tuple[int, int, int] = (10, 10, 15)
    sclera: Tuple[int, int, int] = (245, 245, 250)
    iris_outer: Tuple[int, int, int] = (50, 140, 200)
    iris_inner: Tuple[int, int, int] = (80, 180, 240)
    pupil: Tuple[int, int, int] = (5, 5, 10)
    eyelid: Tuple[int, int, int] = (10, 10, 15)
    text: Tuple[int, int, int] = (250, 250, 255)
    message_bg: Tuple[int, int, int] = (20, 25, 35)
    message_border: Tuple[int, int, int] = (60, 120, 200)
    listening_primary: Tuple[int, int, int] = (80, 250, 150)
    listening_secondary: Tuple[int, int, int] = (50, 200, 120)
    thinking_primary: Tuple[int, int, int] = (255, 180, 80)
    thinking_secondary: Tuple[int, int, int] = (200, 140, 60)

@dataclass
class EyeConfig:
    """Eye configuration"""
    width: int = 480
    height: int = 480
    border_radius: int = 240
    iris_diameter: int = 280
    pupil_diameter: int = 140
    lerp_speed: float = 0.12
    blink_duration: float = 0.15
    min_blink_interval: float = 2.5
    max_blink_interval: float = 6.0
    movement_range_x: int = 25
    movement_range_y: int = 18

# ============================================================================
# LAYOUT MANAGER
# ============================================================================

class LayoutManager:
    """Smart responsive layout"""
    
    def __init__(self, screen_size: Tuple[int, int], eye_config: EyeConfig):
        self.screen_width, self.screen_height = screen_size
        self.eye_config = eye_config
        self._calculate_layout()
    
    def _calculate_layout(self):
        """Calculate all positions"""
        # Eyes - centered vertically
        self.eye_y_pos = (self.screen_height // 2) - (self.eye_config.height // 2)
        eye_spacing = self.screen_width * 0.12
        self.left_eye_x = (self.screen_width // 2) - self.eye_config.width - eye_spacing
        self.right_eye_x = (self.screen_width // 2) + eye_spacing
        
        # Center point ABOVE eyes for indicators
        self.center_x = self.screen_width // 2
        self.indicator_y = self.eye_y_pos - 100  # 100px above eyes
        
        # Message box - modern design
        msg_width = min(self.screen_width * 0.8, 1600)
        msg_height = min(self.screen_height * 0.7, 800)
        msg_x = (self.screen_width - msg_width) // 2
        msg_y = (self.screen_height - msg_height) // 2
        self.message_box = pygame.Rect(msg_x, msg_y, msg_width, msg_height)
        
        # Text area with proper padding
        padding = 50
        self.text_area = pygame.Rect(
            msg_x + padding,
            msg_y + padding,
            msg_width - (padding * 2),
            msg_height - (padding * 2)
        )
    
    def update(self, new_size: Tuple[int, int]):
        """Update on resize"""
        self.screen_width, self.screen_height = new_size
        self._calculate_layout()
    
    def get_eye_positions(self) -> Tuple[int, int]:
        """Get eye X positions"""
        return self.left_eye_x, self.right_eye_x

# ============================================================================
# EYE ANIMATOR
# ============================================================================

class EyeAnimator:
    """Advanced eye animations"""
    
    def __init__(self, config: EyeConfig):
        self.config = config
        
        # Blink state
        self.is_blinking = False
        self.blink_start_time = 0
        self.next_blink_time = time.time() + random.uniform(
            config.min_blink_interval, config.max_blink_interval
        )
        
        # Movement state
        self.current_offset_x = 0.0
        self.current_offset_y = 0.0
        self.target_offset_x = 0.0
        self.target_offset_y = 0.0
        self.next_move_time = time.time() + 1.0
        
        # Pupil dilation (0.8 to 1.2)
        self.pupil_scale = 1.0
        self.target_pupil_scale = 1.0
        
        # Focus level
        self.focus_level = 0.5
    
    def update(self, dt: float, state: FaceState):
        """Update animations"""
        current_time = time.time()
        
        # State-based behavior
        if state == FaceState.LISTENING:
            self.focus_level = 0.95
            self.target_pupil_scale = 1.15
            move_interval = (0.3, 1.0)
        elif state == FaceState.THINKING:
            self.focus_level = 0.8
            self.target_pupil_scale = 1.05
            move_interval = (0.2, 0.8)
        else:
            self.focus_level = 0.5
            self.target_pupil_scale = 1.0
            move_interval = (1.0, 3.0)
        
        # Smooth pupil dilation
        self.pupil_scale += (self.target_pupil_scale - self.pupil_scale) * 0.05
        
        # Blink logic
        if current_time > self.next_blink_time and not self.is_blinking:
            self.start_blink()
        
        if self.is_blinking and current_time - self.blink_start_time > self.config.blink_duration:
            self.is_blinking = False
        
        # Movement logic
        if current_time > self.next_move_time:
            movement_scale = self.focus_level
            self.target_offset_x = random.uniform(
                -self.config.movement_range_x * movement_scale,
                self.config.movement_range_x * movement_scale
            )
            self.target_offset_y = random.uniform(
                -self.config.movement_range_y * movement_scale,
                self.config.movement_range_y * movement_scale
            )
            self.next_move_time = current_time + random.uniform(*move_interval)
        
        # Smooth movement
        lerp_speed = self.config.lerp_speed * (1 + self.focus_level * 0.5)
        self.current_offset_x += (self.target_offset_x - self.current_offset_x) * lerp_speed
        self.current_offset_y += (self.target_offset_y - self.current_offset_y) * lerp_speed
    
    def start_blink(self):
        """Start blink"""
        self.is_blinking = True
        self.blink_start_time = time.time()
        self.next_blink_time = time.time() + self.config.blink_duration + random.uniform(
            self.config.min_blink_interval, self.config.max_blink_interval
        )
    
    def get_blink_amount(self) -> float:
        """Get blink progress (0 to 1)"""
        if not self.is_blinking:
            return 0.0
        
        progress = (time.time() - self.blink_start_time) / self.config.blink_duration
        return abs(math.sin(progress * math.pi))

# ============================================================================
# MODERN EYE RENDERER
# ============================================================================

class EyeRenderer:
    """Modern eye rendering with gradients"""
    
    def __init__(self, config: EyeConfig, colors: ColorScheme):
        self.config = config
        self.colors = colors
    
    def draw_gradient_circle(self, surface, center, radius, color_inner, color_outer):
        """Draw circular gradient"""
        for i in range(radius, 0, -2):
            ratio = i / radius
            color = tuple(
                int(color_inner[j] * (1 - ratio) + color_outer[j] * ratio)
                for j in range(3)
            )
            pygame.draw.circle(surface, color, center, i)
    
    def draw_eye(self, surface: pygame.Surface, x: int, y: int, 
                 offset_x: float, offset_y: float, blink_amount: float, pupil_scale: float):
        """Draw modern eye with effects"""
        
        # Sclera
        eye_rect = pygame.Rect(x, y, self.config.width, self.config.height)
        pygame.draw.rect(surface, self.colors.sclera, eye_rect, border_radius=self.config.border_radius)
        
        # Iris and pupil positions
        iris_x = x + (self.config.width / 2) + offset_x
        iris_y = y + (self.config.height / 2) + offset_y
        
        # Iris with gradient
        self.draw_gradient_circle(
            surface, (int(iris_x), int(iris_y)),
            self.config.iris_diameter // 2,
            self.colors.iris_inner, self.colors.iris_outer
        )
        
        # Pupil with scaling
        pupil_size = int((self.config.pupil_diameter // 2) * pupil_scale)
        pygame.draw.circle(surface, self.colors.pupil, (int(iris_x), int(iris_y)), pupil_size)
        
        # Light reflections
        pygame.draw.circle(surface, (255, 255, 255), 
                         (int(iris_x - 25), int(iris_y - 25)), 12)
        pygame.draw.circle(surface, (200, 200, 200), 
                         (int(iris_x + 30), int(iris_y + 20)), 6)
        
        # Eyelids (blink effect)
        if blink_amount > 0:
            lid_height = blink_amount * (self.config.height / 2 + 10)
            
            # Top eyelid
            top_rect = pygame.Rect(x - 10, y - 20, self.config.width + 20, lid_height + 20)
            pygame.draw.rect(surface, self.colors.eyelid, top_rect)
            
            # Bottom eyelid
            bottom_y = y + self.config.height - lid_height
            bottom_rect = pygame.Rect(x - 10, bottom_y, self.config.width + 20, lid_height + 20)
            pygame.draw.rect(surface, self.colors.eyelid, bottom_rect)

# ============================================================================
# TEXT RENDERER WITH TYPING ANIMATION
# ============================================================================

class TextRenderer:
    """Text with realistic typing animation + full multiline support"""

    def __init__(self, font_name: str = "segoeui"):
        self.font_name = font_name
        self.base_font_size = 70
        self.min_font_size = 35
        self.font_cache = {}

        # Typing animation
        self.target_text = ""
        self.current_index = 0
        self.next_char_time = 0
        self.typing_speed = 0.04  

        # Cursor
        self.cursor_visible = True
        self.cursor_toggle_time = 0

        self._init_fonts()

    def _init_fonts(self):
        """Load fonts"""
        for size in range(35, 100, 5):
            try:
                self.font_cache[size] = pygame.font.SysFont(self.font_name, size)
            except:
                self.font_cache[size] = pygame.font.Font(None, size)

    def _get_font(self, size: int):
        size = (size // 5) * 5
        if size not in self.font_cache:
            try:
                self.font_cache[size] = pygame.font.SysFont(self.font_name, size)
            except:
                self.font_cache[size] = pygame.font.Font(None, size)
        return self.font_cache[size]

    def set_text(self, text: str):
        self.target_text = text
        self.current_index = 0
        self.next_char_time = time.time()

    def update(self, dt: float):
        now = time.time()

        # cursor blinking
        if now > self.cursor_toggle_time:
            self.cursor_visible = not self.cursor_visible
            self.cursor_toggle_time = now + 0.5

        # typing animation
        if now > self.next_char_time and self.current_index < len(self.target_text):
            self.current_index += 1

            ch = self.target_text[self.current_index - 1]
            if ch in ".!?":
                delay = 0.28
            elif ch in ",;:":
                delay = 0.14
            elif ch == " ":
                delay = 0.05
            else:
                delay = random.uniform(0.03, 0.07)

            self.next_char_time = now + delay

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        """Perfect wrap + newline support"""
        final = []

        # Split by newline first
        paragraphs = text.split("\n")

        for para in paragraphs:
            para = para.strip()

            if para == "":
                final.append("")
                continue

            words = para.split(" ")
            line = ""

            for w in words:
                test = (line + " " + w).strip()
                if font.size(test)[0] <= max_width:
                    line = test
                else:
                    if line:
                        final.append(line)
                    line = w

            if line:
                final.append(line)

        return final

    def _calculate_best_font_size(self, text: str, max_width: int, max_height: int):
        for size in range(self.base_font_size, self.min_font_size, -5):
            font = self._get_font(size)
            lines = self._wrap_text(text, font, max_width)
            h = len(lines) * font.get_linesize()
            if h <= max_height:
                return size

        return self.min_font_size

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, color):
        if not self.target_text:
            return

        # currently typed text
        txt = self.target_text[:self.current_index]

        if self.cursor_visible and self.current_index < len(self.target_text):
            txt += "▌"

        font_size = self._calculate_best_font_size(self.target_text, rect.width, rect.height)
        font = self._get_font(font_size)

        lines = self._wrap_text(txt, font, rect.width)
        lh = font.get_linesize()

        total_h = len(lines) * lh
        start_y = rect.y + (rect.height - total_h) // 2

        for i, line in enumerate(lines):
            surf = font.render(line, True, color)
            r = surf.get_rect(center=(rect.centerx, start_y + i * lh + lh // 2))
            surface.blit(surf, r)

    def is_complete(self):
        return self.current_index >= len(self.target_text)


# ============================================================================
# MODERN INDICATOR RENDERER
# ============================================================================

class IndicatorRenderer:
    """Beautiful state indicators ABOVE eyes"""
    
    def __init__(self, colors: ColorScheme):
        self.colors = colors
    
    def draw_listening(self, surface: pygame.Surface, x: int, y: int, pulse: float):
        """Draw listening indicator - Audio waveform style"""
        # Pulsing effect
        pulse_val = abs(math.sin(pulse)) * 0.5 + 0.5
        
        # Background glow
        for i in range(5, 0, -1):
            alpha = int(40 * pulse_val / i)
            glow_size = 120 + (i * 20)
            s = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            color = (*self.colors.listening_primary, alpha)
            pygame.draw.circle(s, color, (glow_size // 2, glow_size // 2), glow_size // 2)
            surface.blit(s, (x - glow_size // 2, y - glow_size // 2))
        
        # Animated sound waves (bars)
        num_bars = 7
        bar_width = 8
        bar_spacing = 14
        total_width = num_bars * bar_spacing
        start_x = x - total_width // 2
        
        for i in range(num_bars):
            # Each bar oscillates differently
            wave_offset = math.sin(pulse * 2.5 + i * 0.5) * 0.5 + 0.5
            bar_height = 15 + wave_offset * 45
            
            bar_x = start_x + i * bar_spacing
            bar_y = y - bar_height // 2
            
            # Gradient bar
            for h in range(int(bar_height)):
                ratio = h / bar_height
                color = tuple(
                    int(self.colors.listening_primary[j] * (1 - ratio * 0.3))
                    for j in range(3)
                )
                pygame.draw.rect(surface, color, 
                               (bar_x, bar_y + h, bar_width, 1))
            
            # Bar outline
            pygame.draw.rect(surface, self.colors.listening_secondary,
                           (bar_x, bar_y, bar_width, int(bar_height)), 
                           width=1, border_radius=2)
        
        # Label with modern font
        try:
            font = pygame.font.SysFont("segoeui", 24, bold=True)
            text = font.render("● LISTENING", True, self.colors.listening_primary)
            text_rect = text.get_rect(center=(x, y + 55))
            
            # Text shadow
            shadow = font.render("● LISTENING", True, (0, 0, 0))
            shadow_rect = shadow.get_rect(center=(x + 2, y + 57))
            surface.blit(shadow, shadow_rect)
            surface.blit(text, text_rect)
        except:
            pass
    
    def draw_thinking(self, surface: pygame.Surface, x: int, y: int, rotation: float):
        """Draw thinking indicator - Neural network style"""
        # Brain/neural style with connected nodes
        
        # Background glow pulse
        glow_pulse = abs(math.sin(rotation * 0.03)) * 0.3 + 0.7
        for i in range(5, 0, -1):
            alpha = int(50 * glow_pulse / i)
            glow_size = 140 + (i * 15)
            s = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            color = (*self.colors.thinking_primary, alpha)
            pygame.draw.circle(s, color, (glow_size // 2, glow_size // 2), glow_size // 2)
            surface.blit(s, (x - glow_size // 2, y - glow_size // 2))
        
        # Neural nodes in hexagonal pattern
        nodes = []
        
        # Center node
        nodes.append((x, y))
        
        # Ring of 6 nodes
        for i in range(6):
            angle = math.radians(rotation + i * 60)
            radius = 50
            node_x = x + math.cos(angle) * radius
            node_y = y + math.sin(angle) * radius
            nodes.append((node_x, node_y))
        
        # Draw connections (synapses)
        for i in range(1, len(nodes)):
            # Pulsing connection strength
            pulse = abs(math.sin(rotation * 0.05 + i * 0.3)) * 0.5 + 0.5
            alpha = int(100 * pulse)
            
            s = pygame.Surface((self.colors.thinking_primary[0] + 100, 
                               self.colors.thinking_primary[1] + 100), pygame.SRCALPHA)
            
            start_pos = (int(nodes[0][0]), int(nodes[0][1]))
            end_pos = (int(nodes[i][0]), int(nodes[i][1]))
            
            pygame.draw.line(surface, (*self.colors.thinking_secondary, alpha),
                           start_pos, end_pos, 2)
        
        # Draw nodes
        for i, (node_x, node_y) in enumerate(nodes):
            # Pulsing size
            pulse = abs(math.sin(rotation * 0.04 + i * 0.4)) * 0.3 + 0.7
            
            if i == 0:  # Center node is larger
                node_size = int(14 * pulse)
                color = self.colors.thinking_primary
            else:
                node_size = int(10 * pulse)
                color = self.colors.thinking_secondary
            
            # Node glow
            glow_surf = pygame.Surface((node_size * 4, node_size * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*color, 80), 
                             (node_size * 2, node_size * 2), node_size * 2)
            surface.blit(glow_surf, (int(node_x - node_size * 2), int(node_y - node_size * 2)))
            
            # Node core
            pygame.draw.circle(surface, color, (int(node_x), int(node_y)), node_size)
            pygame.draw.circle(surface, (255, 255, 255), (int(node_x), int(node_y)), node_size // 2)
        
        # Label
        try:
            font = pygame.font.SysFont("segoeui", 24, bold=True)
            text = font.render("⚡ THINKING", True, self.colors.thinking_primary)
            text_rect = text.get_rect(center=(x, y + 80))
            
            # Text shadow
            shadow = font.render("⚡ THINKING", True, (0, 0, 0))
            shadow_rect = shadow.get_rect(center=(x + 2, y + 82))
            surface.blit(shadow, shadow_rect)
            surface.blit(text, text_rect)
        except:
            pass

# ============================================================================
# COMMAND HANDLER
# ============================================================================

class CommandHandler:
    """Socket command handler"""
    
    def __init__(self, port: int = 5002):
        self.port = port
        self.current_command: Optional[dict] = None
        self.command_lock = threading.Lock()
        self.running = True
    
    def start(self):
        """Start server"""
        thread = threading.Thread(target=self._server_loop, daemon=True)
        thread.start()
        print(f"[Saira V10] Socket server on 127.0.0.1:{self.port}")
    
    def _server_loop(self):
        """Server loop"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", self.port))
            sock.listen()
            
            while self.running:
                try:
                    conn, addr = sock.accept()
                    data = self._receive_data(conn)
                    
                    if data:
                        try:
                            cmd = json.loads(data.decode('utf-8').strip())
                            with self.command_lock:
                                self.current_command = cmd
                            print(f"[Saira] Command: {cmd.get('cmd', 'unknown')}")
                        except json.JSONDecodeError:
                            pass
                    
                    conn.close()
                except:
                    pass
        except Exception as e:
            print(f"[Saira] Server error: {e}")
    
    def _receive_data(self, conn: socket.socket) -> bytes:
        """Receive data"""
        data = b""
        while True:
            try:
                chunk = conn.recv(1024)
                if not chunk or b"\n" in chunk:
                    data += chunk
                    break
                data += chunk
            except:
                break
        return data
    
    def get_command(self) -> Optional[dict]:
        """Get pending command"""
        with self.command_lock:
            cmd = self.current_command
            self.current_command = None
            return cmd
    
    def stop(self):
        """Stop server"""
        self.running = False

# ============================================================================
# MAIN FACE APPLICATION
# ============================================================================

class FaceApplication:
    """Perfect Saira face with everything"""
    
    def __init__(self):
        # Configuration
        self.display_config = DisplayConfig()
        self.colors = ColorScheme()
        self.eye_config = EyeConfig()
        
        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode(
            (self.display_config.start_width, self.display_config.start_height),
            pygame.RESIZABLE
        )
        pygame.display.set_caption("🤖 Saira's Face V10 - Perfect Edition")
        
        # Components
        self.layout = LayoutManager(self.screen.get_size(), self.eye_config)
        self.eye_animator = EyeAnimator(self.eye_config)
        self.eye_renderer = EyeRenderer(self.eye_config, self.colors)
        self.text_renderer = TextRenderer()
        self.indicator_renderer = IndicatorRenderer(self.colors)
        self.command_handler = CommandHandler()
        
        # State
        self.state = FaceState.IDLE
        self.fullscreen = False
        self.running = True
        self.clock = pygame.time.Clock()
        
        # Animation states
        self.listening_pulse = 0.0
        self.thinking_rotation = 0.0
        
        # Start server
        self.command_handler.start()
        
        print("=" * 70)
        print("🤖 SAIRA FACE SYSTEM V10 - PERFECT EDITION")
        print("=" * 70)
        print("✨ Features:")
        print("  • Realistic typing animation (character by character)")
        print("  • Modern indicators ABOVE eyes")
        print("  • Listening: Audio waveform bars")
        print("  • Thinking: Neural network nodes")
        print("  • Gradient eyes with pupil dilation")
        print("  • Smooth 60fps animations")
        print("\n🎮 Controls:")
        print("  • F11: Toggle fullscreen")
        print("  • ESC: Exit")
        print("=" * 70 + "\n")
    
    def handle_events(self):
        """Handle events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                self.layout.update(event.size)
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_F11:
                    self.toggle_fullscreen()
    
    def toggle_fullscreen(self):
        """Toggle fullscreen"""
        self.fullscreen = not self.fullscreen
        
        if self.fullscreen:
            self.screen = pygame.display.set_mode(
                (self.display_config.fullscreen_width, self.display_config.fullscreen_height),
                pygame.FULLSCREEN
            )
        else:
            self.screen = pygame.display.set_mode(
                (self.display_config.start_width, self.display_config.start_height),
                pygame.RESIZABLE
            )
        
        self.layout.update(self.screen.get_size())
    
    def handle_commands(self):
        """Process commands"""
        cmd = self.command_handler.get_command()
        if not cmd:
            return
        
        cmd_type = cmd.get("cmd")
        
        if cmd_type == "talk":
            if cmd.get("state"):
                self.state = FaceState.TALKING
                self.text_renderer.set_text(cmd.get("text", "..."))
            else:
                self.state = FaceState.IDLE
        
        elif cmd_type == "listen":
            self.state = FaceState.LISTENING
        
        elif cmd_type == "think":
            self.state = FaceState.THINKING
        
        elif cmd_type == "idle":
            self.state = FaceState.IDLE
    
    def update(self, dt: float):
        """Update state"""
        self.handle_commands()
        
        if self.state != FaceState.TALKING:
            self.eye_animator.update(dt, self.state)
        
        if self.state == FaceState.TALKING:
            self.text_renderer.update(dt)
        
        elif self.state == FaceState.LISTENING:
            self.listening_pulse += dt * 3
        
        elif self.state == FaceState.THINKING:
            self.thinking_rotation += dt * 100
    
    def draw(self):
        """Render frame"""
        self.screen.fill(self.colors.background)
        
        if self.state in [FaceState.IDLE, FaceState.LISTENING, FaceState.THINKING]:
            # Draw indicators ABOVE eyes first
            if self.state == FaceState.LISTENING:
                self.indicator_renderer.draw_listening(
                    self.screen, self.layout.center_x, self.layout.indicator_y,
                    self.listening_pulse
                )
            
            elif self.state == FaceState.THINKING:
                self.indicator_renderer.draw_thinking(
                    self.screen, self.layout.center_x, self.layout.indicator_y,
                    self.thinking_rotation
                )
            
            # Draw eyes below indicators
            left_x, right_x = self.layout.get_eye_positions()
            blink = self.eye_animator.get_blink_amount()
            
            for eye_x in [left_x, right_x]:
                self.eye_renderer.draw_eye(
                    self.screen, eye_x, self.layout.eye_y_pos,
                    self.eye_animator.current_offset_x,
                    self.eye_animator.current_offset_y,
                    blink,
                    self.eye_animator.pupil_scale
                )
        
        elif self.state == FaceState.TALKING:
            # Modern message box with border glow
            # Outer glow
            glow_rect = self.layout.message_box.inflate(10, 10)
            s = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(s, (*self.colors.message_border, 80), 
                           s.get_rect(), border_radius=25)
            self.screen.blit(s, glow_rect.topleft)
            
            # Main box
            pygame.draw.rect(self.screen, self.colors.message_bg,
                           self.layout.message_box, border_radius=20)
            pygame.draw.rect(self.screen, self.colors.message_border,
                           self.layout.message_box, width=3, border_radius=20)
            
            # Text with typing animation
            self.text_renderer.draw(
                self.screen, self.layout.text_area, self.colors.text
            )
        
        pygame.display.flip()
    
    def run(self):
        """Main loop"""
        while self.running:
            dt = self.clock.tick(self.display_config.target_fps) / 1000.0
            
            self.handle_events()
            self.update(dt)
            self.draw()
        
        self.command_handler.stop()
        pygame.quit()
        print("\n👋 Saira Face V10 Perfect Edition signing off!")

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app = FaceApplication()
    app.run()
