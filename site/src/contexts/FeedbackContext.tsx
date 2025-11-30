import { createContext, useContext, useState, ReactNode } from 'react';

interface FeedbackContextType {
  openFeedback: (context?: FeedbackContext) => void;
}

interface FeedbackContext {
  type: 'general' | 'model' | 'feature' | 'bug';
  modelName?: string;
  modelId?: string;
  section?: string;
}

const FeedbackContext = createContext<FeedbackContextType | undefined>(undefined);

export const FeedbackProvider = ({ children }: { children: ReactNode }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [context, setContext] = useState<FeedbackContext>({ type: 'general' });

  const openFeedback = (feedbackContext?: FeedbackContext) => {
    setContext(feedbackContext || { type: 'general' });
    setIsOpen(true);
  };

  return (
    <FeedbackContext.Provider value={{ openFeedback }}>
      {children}
      {/* The FeedbackDialog will be rendered here */}
    </FeedbackContext.Provider>
  );
};

export const useFeedback = () => {
  const context = useContext(FeedbackContext);
  if (!context) {
    throw new Error('useFeedback must be used within FeedbackProvider');
  }
  return context;
};