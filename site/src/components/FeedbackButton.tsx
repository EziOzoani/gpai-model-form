import { MessageSquare, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface FeedbackButtonProps {
  onClick: () => void;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'sm' | 'default' | 'lg';
  className?: string;
  showText?: boolean;
  showTooltip?: boolean;
}

export const FeedbackButton = ({
  onClick,
  variant = 'outline',
  size = 'default',
  className,
  showText = true,
  showTooltip = true
}: FeedbackButtonProps) => {
  const button = (
    <Button
      variant={variant}
      size={size}
      onClick={onClick}
      className={cn("flex items-center gap-2", className)}
    >
      <MessageSquare className="h-4 w-4" />
      {showText && 'Feedback'}
      {showTooltip && <Info className="h-3 w-3" />}
    </Button>
  );

  if (showTooltip) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          {button}
        </TooltipTrigger>
        <TooltipContent>
          <p>We welcome comments, corrections, insights and more</p>
        </TooltipContent>
      </Tooltip>
    );
  }

  return button;
};