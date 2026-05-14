"""Database module using SQLite for local storage.

Handles database operations for users, inventory, cards, and drops.
No external database server needed.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from config import config
from .logger import log

def _serialize_data(data: Dict[str, Any]) -> str:
    """Convert data to JSON, handling datetime objects."""
    clean_data = {}
    for key, value in data.items():
        if hasattr(value, 'isoformat'):  # datetime object
            clean_data[key] = value.isoformat()
        else:
            clean_data[key] = value
    return json.dumps(clean_data)


class Database:
    """SQLite database handler with async-like interface."""
    
    def __init__(self):
        self.db_path = Path("bot_database.db")
        self.conn = None
        
    async def connect(self) -> bool:
        """Connect to SQLite database.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            
            # Create tables
            await self._create_tables()
            log.info("Connected to SQLite database")
            return True
            
        except Exception as e:
            log.error(f"Failed to connect to database: {e}")
            return False
    
    async def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            log.info("Database connection closed")
    
    async def _create_tables(self):
        """Create database tables."""
        try:
            cursor = self.conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    balance INTEGER DEFAULT 0,
                    cards_count INTEGER DEFAULT 0,
                    last_daily TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Inventory table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    card_id TEXT NOT NULL,
                    card_data TEXT NOT NULL,
                    obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, card_id),
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Cards table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cards (
                    card_id TEXT PRIMARY KEY,
                    card_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Drops table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    drop_id TEXT UNIQUE,
                    drop_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.conn.commit()
            log.debug("Database tables created")
        except Exception as e:
            log.warning(f"Table creation warning: {e}")
    
    # ==================== USER OPERATIONS ====================
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            User document or None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    async def create_user(self, user_id: int, username: str) -> Dict[str, Any]:
        """Create new user profile.
        
        Args:
            user_id: Discord user ID
            username: Discord username
            
        Returns:
            Created user document
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, username, balance, cards_count)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, config.STARTING_BALANCE, 0))
        self.conn.commit()
        
        return await self.get_user(user_id)
    
    async def get_or_create_user(self, user_id: int, username: str) -> Dict[str, Any]:
        """Get user or create if doesn't exist.
        
        Args:
            user_id: Discord user ID
            username: Discord username
            
        Returns:
            User document
        """
        user = await self.get_user(user_id)
        if not user:
            user = await self.create_user(user_id, username)
        return user
    
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> bool:
        """Update user profile.
        
        Args:
            user_id: Discord user ID
            update_data: Data to update
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            update_data['updated_at'] = datetime.now()
            
            set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
            values = list(update_data.values()) + [user_id]
            
            cursor.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Error updating user: {e}")
            return False
    
    async def add_balance(self, user_id: int, amount: int) -> bool:
        """Add money to user balance.
        
        Args:
            user_id: Discord user ID
            amount: Amount to add
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET balance = balance + ?, updated_at = ?
                WHERE user_id = ?
            ''', (amount, datetime.now(), user_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Error adding balance: {e}")
            return False
    
    async def remove_balance(self, user_id: int, amount: int) -> bool:
        """Remove money from user balance.
        
        Args:
            user_id: Discord user ID
            amount: Amount to remove
            
        Returns:
            True if successful
        """
        return await self.add_balance(user_id, -amount)
    
    # ==================== INVENTORY OPERATIONS ====================
    
    async def add_to_inventory(self, user_id: int, card_id: str, card_data: Dict[str, Any]) -> bool:
        """Add card to user inventory.
        
        Args:
            user_id: Discord user ID
            card_id: Unique card ID
            card_data: Card information
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            card_json = _serialize_data(card_data)
            
            cursor.execute('''
                INSERT INTO inventory (user_id, card_id, card_data)
                VALUES (?, ?, ?)
            ''', (user_id, card_id, card_json))
            
            cursor.execute('''
                UPDATE users 
                SET cards_count = cards_count + 1, updated_at = ?
                WHERE user_id = ?
            ''', (datetime.now(), user_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            log.error(f"Error adding to inventory: {e}")
            return False
    
    async def get_inventory(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user inventory cards.
        
        Args:
            user_id: Discord user ID
            limit: Number of cards to return
            
        Returns:
            List of inventory items
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, user_id, card_id, card_data, obtained_at 
            FROM inventory 
            WHERE user_id = ? 
            LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # ==================== CARD OPERATIONS ====================
    
    async def save_card(self, card_id: str, card_data: Dict[str, Any]) -> bool:
        """Save card data to database.
        
        Args:
            card_id: Unique card ID
            card_data: Card information
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            card_json = _serialize_data(card_data)
            
            cursor.execute('''
                INSERT OR REPLACE INTO cards (card_id, card_data)
                VALUES (?, ?)
            ''', (card_id, card_json))
            
            self.conn.commit()
            return True
        except Exception as e:
            log.error(f"Error saving card: {e}")
            return False
    
    async def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get card data.
        
        Args:
            card_id: Unique card ID
            
        Returns:
            Card document or None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM cards WHERE card_id = ?", (card_id,))
        row = cursor.fetchone()
        
        if row:
            result = dict(row)
            result['card_data'] = json.loads(result['card_data'])
            return result
        return None
    
    # ==================== DROP OPERATIONS ====================
    
    async def create_drop(self, drop_data: Dict[str, Any]) -> bool:
        """Create a new drop.
        
        Args:
            drop_data: Drop information
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            drop_json = _serialize_data(drop_data)
            drop_id = drop_data.get('_id', None)
            
            cursor.execute('''
                INSERT INTO drops (drop_id, drop_data)
                VALUES (?, ?)
            ''', (drop_id, drop_json))
            
            self.conn.commit()
            return True
        except Exception as e:
            log.error(f"Error creating drop: {e}")
            return False
    
    async def update_drop(self, drop_id: str, update_data: Dict[str, Any]) -> bool:
        """Update drop data.
        
        Args:
            drop_id: Drop ID
            update_data: Data to update
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            update_json = _serialize_data(update_data)
            
            cursor.execute('''
                UPDATE drops 
                SET drop_data = ?
                WHERE drop_id = ?
            ''', (update_json, drop_id))
            
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Error updating drop: {e}")
            return False


# Global database instance
db = Database()
