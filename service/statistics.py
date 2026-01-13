import sqlite3
import os
from datetime import datetime, timedelta
from collections import defaultdict
import io

class StatisticsManager:
    """Manages security event logging and statistics generation"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Events table - logs all security events
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                image_path TEXT
            )
        ''')
        
        # Uploads table - tracks upload success/failure
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                filename TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT
            )
        ''')
        
        # Commands table - logs remote commands
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                command TEXT NOT NULL,
                user_id TEXT,
                success BOOLEAN NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_event(self, event_type, details=None, image_path=None):
        """Log a security event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO events (event_type, details, image_path) VALUES (?, ?, ?)',
            (event_type, details, image_path)
        )
        conn.commit()
        conn.close()
    
    def log_upload(self, filename, success, error_message=None):
        """Log an upload attempt"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO uploads (filename, success, error_message) VALUES (?, ?, ?)',
            (filename, success, error_message)
        )
        conn.commit()
        conn.close()
    
    def log_command(self, command, user_id, success):
        """Log a remote command execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO commands (command, user_id, success) VALUES (?, ?, ?)',
            (command, user_id, success)
        )
        conn.commit()
        conn.close()
    
    def get_statistics(self, days=30):
        """Generate comprehensive statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        stats = {}
        
        # Total events
        cursor.execute('SELECT COUNT(*) FROM events')
        stats['total_events'] = cursor.fetchone()[0]
        
        # Events in time range
        cursor.execute(
            'SELECT COUNT(*) FROM events WHERE timestamp >= ?',
            (start_date,)
        )
        stats['events_last_n_days'] = cursor.fetchone()[0]
        
        # Failed login attempts
        cursor.execute(
            'SELECT COUNT(*) FROM events WHERE event_type = "failed_login"'
        )
        stats['total_failed_logins'] = cursor.fetchone()[0]
        
        # Captures taken
        cursor.execute(
            'SELECT COUNT(*) FROM events WHERE event_type = "capture"'
        )
        stats['total_captures'] = cursor.fetchone()[0]
        
        # Upload success rate
        cursor.execute('SELECT COUNT(*) FROM uploads WHERE success = 1')
        successful_uploads = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM uploads')
        total_uploads = cursor.fetchone()[0]
        stats['upload_success_rate'] = (
            (successful_uploads / total_uploads * 100) if total_uploads > 0 else 0
        )
        stats['successful_uploads'] = successful_uploads
        stats['failed_uploads'] = total_uploads - successful_uploads
        
        # Commands executed
        cursor.execute('SELECT COUNT(*) FROM commands')
        stats['total_commands'] = cursor.fetchone()[0]
        
        # Most used commands
        cursor.execute('''
            SELECT command, COUNT(*) as count 
            FROM commands 
            GROUP BY command 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        stats['top_commands'] = cursor.fetchall()
        
        # Events by hour (last 7 days)
        cursor.execute('''
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM events
            WHERE timestamp >= datetime('now', '-7 days')
            AND event_type = 'failed_login'
            GROUP BY hour
            ORDER BY hour
        ''')
        stats['events_by_hour'] = cursor.fetchall()
        
        # Events by day (last 30 days)
        cursor.execute('''
            SELECT DATE(timestamp) as day, COUNT(*) as count
            FROM events
            WHERE timestamp >= datetime('now', '-30 days')
            AND event_type = 'failed_login'
            GROUP BY day
            ORDER BY day
        ''')
        stats['events_by_day'] = cursor.fetchall()
        
        # Last 10 events
        cursor.execute('''
            SELECT event_type, timestamp, details
            FROM events
            ORDER BY timestamp DESC
            LIMIT 10
        ''')
        stats['recent_events'] = cursor.fetchall()
        
        conn.close()
        return stats
    
    def generate_chart(self, stats):
        """Generate a visual chart of statistics using matplotlib"""
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            from matplotlib.dates import DateFormatter
            import matplotlib.dates as mdates
            
            # Create figure with subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
            fig.suptitle('🔒 WatchDog Security Statistics', fontsize=16, fontweight='bold')
            
            # 1. Events by Hour (Heatmap style)
            if stats['events_by_hour']:
                hours = [int(h[0]) for h in stats['events_by_hour']]
                counts = [h[1] for h in stats['events_by_hour']]
                
                # Fill missing hours with 0
                hour_data = [0] * 24
                for h, c in zip(hours, counts):
                    hour_data[h] = c
                
                ax1.bar(range(24), hour_data, color='#FF6B6B', alpha=0.7)
                ax1.set_xlabel('Hour of Day')
                ax1.set_ylabel('Failed Login Attempts')
                ax1.set_title('Attack Patterns by Hour (Last 7 Days)')
                ax1.set_xticks(range(0, 24, 2))
                ax1.grid(axis='y', alpha=0.3)
            else:
                ax1.text(0.5, 0.5, 'No data available', ha='center', va='center')
                ax1.set_title('Attack Patterns by Hour')
            
            # 2. Events by Day (Line chart)
            if stats['events_by_day']:
                days = [datetime.strptime(d[0], '%Y-%m-%d') for d in stats['events_by_day']]
                counts = [d[1] for d in stats['events_by_day']]
                
                ax2.plot(days, counts, marker='o', linewidth=2, markersize=6, color='#4ECDC4')
                ax2.fill_between(days, counts, alpha=0.3, color='#4ECDC4')
                ax2.set_xlabel('Date')
                ax2.set_ylabel('Failed Login Attempts')
                ax2.set_title('Daily Attack Trends (Last 30 Days)')
                ax2.xaxis.set_major_formatter(DateFormatter('%m/%d'))
                ax2.grid(True, alpha=0.3)
                plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
            else:
                ax2.text(0.5, 0.5, 'No data available', ha='center', va='center')
                ax2.set_title('Daily Attack Trends')
            
            # 3. Upload Success Rate (Pie chart)
            if stats['successful_uploads'] + stats['failed_uploads'] > 0:
                sizes = [stats['successful_uploads'], stats['failed_uploads']]
                labels = [f"Success\n({stats['successful_uploads']})", 
                         f"Failed\n({stats['failed_uploads']})"]
                colors = ['#95E1D3', '#FF6B6B']
                explode = (0.05, 0.05)
                
                ax3.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                       startangle=90, explode=explode, shadow=True)
                ax3.set_title('Upload Success Rate')
            else:
                ax3.text(0.5, 0.5, 'No upload data', ha='center', va='center')
                ax3.set_title('Upload Success Rate')
            
            # 4. Top Commands (Horizontal bar chart)
            if stats['top_commands']:
                commands = [cmd[0] for cmd in stats['top_commands']]
                counts = [cmd[1] for cmd in stats['top_commands']]
                
                y_pos = range(len(commands))
                ax4.barh(y_pos, counts, color='#F38181', alpha=0.8)
                ax4.set_yticks(y_pos)
                ax4.set_yticklabels(commands)
                ax4.set_xlabel('Times Used')
                ax4.set_title('Most Used Commands')
                ax4.grid(axis='x', alpha=0.3)
                
                # Add count labels
                for i, v in enumerate(counts):
                    ax4.text(v + 0.1, i, str(v), va='center')
            else:
                ax4.text(0.5, 0.5, 'No command data', ha='center', va='center')
                ax4.set_title('Most Used Commands')
            
            plt.tight_layout()
            
            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except ImportError:
            return None
    
    def format_stats_message(self, stats):
        """Format statistics as a readable text message"""
        msg = "📊 *WatchDog Security Statistics*\n"
        msg += "=" * 35 + "\n\n"
        
        msg += "📈 *Overall Summary*\n"
        msg += f"• Total Events Logged: {stats['total_events']}\n"
        msg += f"• Failed Login Attempts: {stats['total_failed_logins']}\n"
        msg += f"• Photos Captured: {stats['total_captures']}\n"
        msg += f"• Commands Executed: {stats['total_commands']}\n\n"
        
        msg += "📤 *Upload Performance*\n"
        msg += f"• Success Rate: {stats['upload_success_rate']:.1f}%\n"
        msg += f"• Successful: {stats['successful_uploads']}\n"
        msg += f"• Failed: {stats['failed_uploads']}\n\n"
        
        if stats['top_commands']:
            msg += "🎮 *Most Used Commands*\n"
            for cmd, count in stats['top_commands']:
                msg += f"• {cmd}: {count}x\n"
            msg += "\n"
        
        if stats['recent_events']:
            msg += "🕐 *Recent Activity* (Last 10)\n"
            for event_type, timestamp, details in stats['recent_events'][:5]:
                # Format timestamp
                dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                time_str = dt.strftime('%m/%d %H:%M')
                msg += f"• {time_str} - {event_type}\n"
        
        msg += "\n_Use /chart for visual graphs_"
        return msg
