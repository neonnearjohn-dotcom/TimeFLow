# Firestore schema

## users collection
- username: string
- full_name: string
- created_at: timestamp
- achievements_count: number
- stats:
  - habits_completed: number
  - focus_sessions: number
  - tasks_completed: number
  - focus_minutes: number
  - (points field removed)

## achievements collection
- achievement_id: string
- unlocked_at: timestamp
- (reward_points field removed)
