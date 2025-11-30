import { useState, useEffect } from 'react';
import { MessageSquare, Info } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { useToast } from '@/hooks/use-toast';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface FeedbackDialogProps {
  isOpen: boolean;
  onClose: () => void;
  context?: {
    type: 'general' | 'model' | 'feature' | 'bug';
    modelName?: string;
    modelId?: string;
    section?: string;
  };
}

const MODEL_SECTIONS = [
  { value: 'general', label: 'General Information' },
  { value: 'properties', label: 'Model Properties' },
  { value: 'distribution', label: 'Distribution & Licenses' },
  { value: 'use', label: 'Use Cases & Integration' },
  { value: 'data', label: 'Training Data' },
  { value: 'training', label: 'Training Process' },
  { value: 'compute', label: 'Compute Resources' },
  { value: 'energy', label: 'Energy & Emissions' },
  { value: 'other', label: 'Other/General Comments' },
];

export const FeedbackDialog = ({ isOpen, onClose, context = { type: 'general' } }: FeedbackDialogProps) => {
  const { toast } = useToast();
  const [feedbackType, setFeedbackType] = useState(context.type);
  const [modelName, setModelName] = useState(context.modelName || '');
  const [section, setSection] = useState(context.section || 'other');
  const [feedback, setFeedback] = useState('');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setFeedbackType(context.type);
    setModelName(context.modelName || '');
    setSection(context.section || 'other');
  }, [context]);

  const handleSubmit = async () => {
    if (!feedback.trim()) {
      toast({
        title: "Feedback required",
        description: "Please enter your feedback before submitting.",
        variant: "destructive",
      });
      return;
    }

    setSubmitting(true);
    
    const feedbackData = {
      type: feedbackType,
      modelName: feedbackType === 'model' ? modelName : undefined,
      section: feedbackType === 'model' ? section : undefined,
      feedback: feedback.trim(),
      email: email.trim() || undefined,
      name: name.trim() || undefined,
      timestamp: new Date().toISOString(),
    };

    try {
      // Create GitHub issue
      const issueTitle = feedbackType === 'model' 
        ? `[${modelName}] Feedback: ${section ? MODEL_SECTIONS.find(s => s.value === section)?.label : 'General'}`
        : `Dashboard Feedback: ${feedbackType === 'bug' ? 'Bug Report' : feedbackType === 'feature' ? 'Feature Request' : 'General'}`;
      
      const issueBody = `## Feedback Details

**Type:** ${feedbackType === 'model' ? 'Model-Specific' : feedbackType === 'bug' ? 'Bug Report' : feedbackType === 'feature' ? 'Feature Request' : 'General'}
${feedbackType === 'model' ? `**Model:** ${modelName}` : ''}
${feedbackType === 'model' && section ? `**Section:** ${MODEL_SECTIONS.find(s => s.value === section)?.label || section}` : ''}
**Submitted:** ${new Date().toLocaleString()}
${name ? `**Submitted by:** ${name}` : ''}
${email ? `**Contact:** ${email}` : ''}

### Feedback
${feedback}

---
*This issue was automatically created from the GPAI Model Dashboard feedback form.*`;

      // Create the issue using GitHub API
      const response = await fetch('https://api.github.com/repos/EziOzoani/gpai-model-form/issues', {
        method: 'POST',
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'Content-Type': 'application/json',
          // Note: In production, this token should be stored securely on a backend server
          // For now, we'll use a placeholder that needs to be configured
          'Authorization': `token ${import.meta.env.VITE_GITHUB_TOKEN || ''}`
        },
        body: JSON.stringify({
          title: issueTitle,
          body: issueBody,
          labels: feedbackType === 'bug' ? ['bug'] : feedbackType === 'feature' ? ['enhancement'] : ['feedback']
        })
      });

      if (!response.ok) {
        throw new Error(`GitHub API error: ${response.status} ${response.statusText}`);
      }

      const issue = await response.json();
      
      toast({
        title: "Thank you for your feedback!",
        description: `Your feedback has been submitted as issue #${issue.number}.`,
      });
      
      // Reset form
      setFeedback('');
      setEmail('');
      setName('');
      onClose();
    } catch (error) {
      console.error('Error creating GitHub issue:', error);
      
      // Fallback to localStorage if GitHub API fails
      const existingFeedback = JSON.parse(localStorage.getItem('gpai-feedback') || '[]');
      existingFeedback.push(feedbackData);
      localStorage.setItem('gpai-feedback', JSON.stringify(existingFeedback));
      
      toast({
        title: "Feedback saved locally",
        description: "Unable to create GitHub issue. Your feedback has been saved and will be submitted later.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DialogTitle>Share Feedback</DialogTitle>
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-4 w-4 text-muted-foreground cursor-help" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs">We welcome comments, corrections, insights and more</p>
              </TooltipContent>
            </Tooltip>
          </div>
          <DialogDescription>
            Help us improve the GPAI Model Documentation Dashboard
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          {/* Feedback Type */}
          <div className="space-y-2">
            <Label htmlFor="feedback-type">Feedback Type</Label>
            <Select value={feedbackType} onValueChange={(value: any) => setFeedbackType(value)}>
              <SelectTrigger id="feedback-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="general">General Dashboard Feedback</SelectItem>
                <SelectItem value="model">Model-Specific Feedback</SelectItem>
                <SelectItem value="feature">Feature Request</SelectItem>
                <SelectItem value="bug">Bug Report</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Model Name (shown only for model feedback) */}
          {feedbackType === 'model' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="model-name">Model Name</Label>
                <Input
                  id="model-name"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  placeholder="Enter model name"
                  disabled={!!context.modelName}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="section">Section</Label>
                <Select value={section} onValueChange={setSection}>
                  <SelectTrigger id="section">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MODEL_SECTIONS.map((s) => (
                      <SelectItem key={s.value} value={s.value}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </>
          )}

          {/* Feedback Text */}
          <div className="space-y-2">
            <Label htmlFor="feedback">Feedback *</Label>
            <Textarea
              id="feedback"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Share your comments, corrections, or suggestions..."
              rows={6}
              className="resize-none"
            />
          </div>

          {/* Optional Contact Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name (optional)</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email (optional)</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
              />
            </div>
          </div>

          <p className="text-xs text-muted-foreground">
            Contact information is optional and will only be used if we need clarification about your feedback.
          </p>
        </div>

        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            <MessageSquare className="h-4 w-4 mr-2" />
            {submitting ? 'Submitting...' : 'Submit Feedback'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};