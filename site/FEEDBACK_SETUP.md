# Feedback System Setup

The GPAI Model Dashboard feedback system can automatically create GitHub issues when users submit feedback.

## Configuration

1. **Create a GitHub Personal Access Token**
   - Go to https://github.com/settings/tokens
   - Click "Generate new token" → "Generate new token (classic)"
   - Give it a descriptive name (e.g., "GPAI Dashboard Feedback")
   - Select scopes:
     - For public repositories: `public_repo`
     - For private repositories: `repo`
   - Generate the token and copy it

2. **Configure the Dashboard**
   - Copy `.env.example` to `.env.local`:
     ```bash
     cp .env.example .env.local
     ```
   - Edit `.env.local` and add your token:
     ```
     VITE_GITHUB_TOKEN=your_github_personal_access_token_here
     ```

3. **Restart the Development Server**
   ```bash
   npm run dev
   ```

## How It Works

When a user submits feedback:
1. The system creates a GitHub issue with appropriate title and labels
2. Model-specific feedback includes the model name and section
3. Issues are labeled as 'feedback', 'bug', or 'enhancement'
4. If GitHub API fails, feedback is saved locally as a fallback

## Repository Migration

The feedback system currently points to: https://github.com/EziOzoani/gpai-model-form

To change the repository:
1. Update the API URL in `src/components/FeedbackDialog.tsx` line 111
2. Ensure the new repository has issue creation enabled
3. Update your GitHub token if needed for the new repository

## Security Note

In production, the GitHub token should be stored on a secure backend server, not in the frontend. The current implementation is suitable for development and internal use only.