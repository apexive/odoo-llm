# Real-time Notifications for LLM Generation Jobs

## Overview

This implementation provides real-time notifications when LLM generation jobs complete, ensuring that the thread interface updates automatically without requiring a page reload.

## How it Works

### Backend (Python)

1. **Job Completion**: When a webhook is received and processed in `process_webhook_result()`, the system:
   - Updates the job state to 'completed' or 'failed'
   - Posts a message to the associated thread
   - Sends a real-time notification via Odoo's bus system

2. **Real-time Notification**: The `_send_realtime_notification()` method:
   - Creates a notification payload with job and message details
   - Sends it to the current user via `bus.bus._sendone()`
   - Uses the channel 'llm_thread_update'

### Frontend (JavaScript)

1. **Notification Service**: `notification_service.js` provides:
   - A service that listens to bus messages
   - Methods to subscribe/unsubscribe to thread notifications
   - Handling of different notification types

2. **Thread Patch**: `thread_patch.js` extends the LLM thread component to:
   - Subscribe to notifications when the thread is mounted
   - Handle refresh events to update the interface
   - Show toast notifications when jobs complete

## Usage

The system works automatically once the module is installed. When a generation job completes:

1. ✅ The webhook processes the result
2. 📨 A message is posted to the thread
3. 🔔 A real-time notification is sent
4. 🖥️ The frontend receives the notification
5. 🔄 The thread interface updates automatically
6. 🎉 A toast notification appears

## Configuration

No additional configuration is required. The system automatically:
- Detects when jobs complete
- Sends notifications to the appropriate users
- Updates the thread interface in real-time

## Technical Details

- Uses Odoo 16's bus.bus system for real-time communication
- Notifications are sent to the user who owns the thread
- The frontend uses the web bus service to listen for updates
- Thread components are patched to handle notifications
- Error handling ensures the system degrades gracefully
