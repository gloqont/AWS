'use client';

import type { ReactNode } from 'react';

interface TutorialFlowManagerProps {
  children: ReactNode;
}

const TutorialFlowManager = ({ children }: TutorialFlowManagerProps) => {
  return <>{children}</>;
};

export default TutorialFlowManager;
