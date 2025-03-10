# 📂 File Path: /project_root/minigame.py
# 📌 Purpose: This file implements a simple Breakout-style game using Streamlit for interactive visualization.
# 🔄 Latest Changes: Added detailed comments to improve code readability and maintainability.
# ⚙️ Key Logic: Utilizes Streamlit for rendering and PIL for image manipulation to create a playable game interface.
# 🧠 Reasoning: Provides an engaging way to demonstrate interactive graphics capabilities within a web application.

import streamlit as st
import time
import random
import numpy as np
from PIL import Image, ImageDraw

class BreakoutGame:
    def __init__(self, container, width=500, height=300, state=None):
        """
        Initialize a simple Breakout-style game for Streamlit.
        
        Args:
            container: Streamlit container to render the game in
            width (int): Game canvas width
            height (int): Game canvas height
            state (dict, optional): Existing game state for persistence
        """
        self.container = container
        self.width = width
        self.height = height
        
        if state is not None:
            self.game_state = state
        else:
            # Initialize game state
            self.game_state = {
                'width': self.width,
                'height': self.height,
                'score': 0,
                'lives': 3,
                'game_over': False,
                # Paddle properties
                'paddle': {
                    'width': 80,
                    'height': 10,
                    'x': self.width // 2 - 40,
                    'y': self.height - 20,
                    'speed': 8
                },
                # Ball properties
                'ball': {
                    'radius': 6,
                    'x': self.width // 2,
                    'y': self.height // 2,
                    'dx': 3,
                    'dy': -3
                },
                # Brick properties
                'bricks': []
            }
            self.create_bricks()
    
    def create_bricks(self):
        """Create a set of bricks for the game."""
        brick_width = 40
        brick_height = 15
        brick_padding = 5
        brick_offset_top = 30
        
        # Calculate how many bricks can fit in a row
        bricks_per_row = (self.width - brick_padding) // (brick_width + brick_padding)
        
        # Create 3 rows of bricks
        for row in range(3):
            for col in range(bricks_per_row):
                self.game_state['bricks'].append({
                    'x': col * (brick_width + brick_padding) + brick_padding,
                    'y': row * (brick_height + brick_padding) + brick_offset_top,
                    'width': brick_width,
                    'height': brick_height,
                    'color': random.choice(['red', 'orange', 'yellow', 'green', 'blue'])
                })
    
    def update_game(self):
        """Update the game state."""
        game = self.game_state
        
        if game['game_over']:
            return
        
        # Simple AI paddle movement - always follow the ball
        paddle_center = game['paddle']['x'] + game['paddle']['width'] / 2
        target_x = game['ball']['x']
        
        # Move paddle towards the ball
        if paddle_center < target_x - 5:
            game['paddle']['x'] = min(
                game['width'] - game['paddle']['width'], 
                game['paddle']['x'] + game['paddle']['speed']
            )
        elif paddle_center > target_x + 5:
            game['paddle']['x'] = max(0, game['paddle']['x'] - game['paddle']['speed'])
        
        # Move ball
        game['ball']['x'] += game['ball']['dx']
        game['ball']['y'] += game['ball']['dy']
        
        # Ball collision with walls
        if game['ball']['x'] - game['ball']['radius'] < 0 or game['ball']['x'] + game['ball']['radius'] > game['width']:
            game['ball']['dx'] = -game['ball']['dx']
        
        if game['ball']['y'] - game['ball']['radius'] < 0:
            game['ball']['dy'] = -game['ball']['dy']
        
        # Ball collision with paddle
        if (game['ball']['y'] + game['ball']['radius'] > game['paddle']['y'] and
            game['ball']['y'] + game['ball']['radius'] < game['paddle']['y'] + game['paddle']['height'] and
            game['ball']['x'] > game['paddle']['x'] and
            game['ball']['x'] < game['paddle']['x'] + game['paddle']['width']):
            game['ball']['dy'] = -abs(game['ball']['dy'])  # Always bounce up
        
        # Ball collision with bricks
        for brick in game['bricks'][:]:
            if (game['ball']['x'] > brick['x'] and
                game['ball']['x'] < brick['x'] + brick['width'] and
                game['ball']['y'] > brick['y'] and
                game['ball']['y'] < brick['y'] + brick['height']):
                game['ball']['dy'] = -game['ball']['dy']
                game['bricks'].remove(brick)
                game['score'] += 10
        
        # Ball falls below paddle
        if game['ball']['y'] + game['ball']['radius'] > game['height']:
            game['lives'] -= 1
            if game['lives'] <= 0:
                game['game_over'] = True
            else:
                # Reset ball position
                game['ball']['x'] = game['width'] // 2
                game['ball']['y'] = game['height'] // 2
                game['ball']['dx'] = 3 * (1 if random.random() > 0.5 else -1)
                game['ball']['dy'] = -3
        
        # Win condition - add new bricks
        if len(game['bricks']) == 0:
            self.create_bricks()
            # Increase ball speed slightly
            game['ball']['dx'] *= 1.1
            game['ball']['dy'] *= 1.1
    
    def render(self):
        """Render the game."""
        try:
            # Update game state
            self.update_game()
            game = self.game_state
            
            # Create a blank image
            img = Image.new('RGB', (game['width'], game['height']), (0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw paddle
            draw.rectangle(
                [
                    game['paddle']['x'], 
                    game['paddle']['y'], 
                    game['paddle']['x'] + game['paddle']['width'], 
                    game['paddle']['y'] + game['paddle']['height']
                ],
                fill='white'
            )
            
            # Draw ball
            draw.ellipse(
                [
                    game['ball']['x'] - game['ball']['radius'], 
                    game['ball']['y'] - game['ball']['radius'],
                    game['ball']['x'] + game['ball']['radius'], 
                    game['ball']['y'] + game['ball']['radius']
                ],
                fill='white'
            )
            
            # Draw bricks
            for brick in game['bricks']:
                draw.rectangle(
                    [
                        brick['x'], 
                        brick['y'], 
                        brick['x'] + brick['width'], 
                        brick['y'] + brick['height']
                    ],
                    fill=brick['color']
                )
            
            # Draw score and lives
            self.container.markdown(f"### Score: {game['score']} | Lives: {game['lives']}")
            
            # Display game canvas
            self.container.image(img, use_column_width=False)
            
            # Game over message
            if game['game_over']:
                self.container.error(f"Game Over! Final Score: {game['score']}")
                return False
            
            # Small delay
            time.sleep(0.05)
            
            return True
            
        except Exception as e:
            self.container.error(f"Game error: {str(e)}")
            return False 