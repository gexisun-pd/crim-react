import React, { useState } from 'react';
import { Music, FileText, TestTube } from 'lucide-react';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from './ui/sidebar';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';
import PieceViewer from '../pages/PieceViewer';
import OSMDTest from './OSMDTest';

type ViewType = 'piece-viewer' | 'osmd-test';

const AppContent: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewType>('piece-viewer');
  const { setOpenMobile, toggleSidebar, isMobile, state } = useSidebar();

  const handleViewChange = (view: ViewType) => {
    setCurrentView(view);
    // Auto-close sidebar only on mobile after selection
    if (isMobile) {
      setOpenMobile(false);
    }
  };

  const getPageTitle = () => {
    switch (currentView) {
      case 'piece-viewer':
        return 'Piece Viewer';
      case 'osmd-test':
        return 'OSMD Test';
      default:
        return 'Music Analysis';
    }
  };

  const renderContent = () => {
    switch (currentView) {
      case 'piece-viewer':
        return <PieceViewer />;
      case 'osmd-test':
        return <OSMDTest />;
      default:
        return <PieceViewer />;
    }
  };

  return (
    <>
      <Sidebar collapsible="icon">
        <SidebarHeader>
          <div className="flex items-center gap-2 px-4 py-2">
            <Music className="h-6 w-6 text-primary" />
            {state === 'expanded' && <h1 className="text-lg font-semibold">Music Analysis</h1>}
          </div>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            {state === 'expanded' && <SidebarGroupLabel>Navigation</SidebarGroupLabel>}
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <SidebarMenuButton
                          onClick={() => handleViewChange('piece-viewer')}
                          isActive={currentView === 'piece-viewer'}
                        >
                          <FileText className="h-4 w-4" />
                          {state === 'expanded' && <span>Piece Viewer</span>}
                        </SidebarMenuButton>
                      </TooltipTrigger>
                      {state === 'collapsed' && (
                        <TooltipContent side="right">
                          <p>Piece Viewer</p>
                        </TooltipContent>
                      )}
                    </Tooltip>
                  </TooltipProvider>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <SidebarMenuButton
                          onClick={() => handleViewChange('osmd-test')}
                          isActive={currentView === 'osmd-test'}
                        >
                          <TestTube className="h-4 w-4" />
                          {state === 'expanded' && <span>OSMD Test</span>}
                        </SidebarMenuButton>
                      </TooltipTrigger>
                      {state === 'collapsed' && (
                        <TooltipContent side="right">
                          <p>OSMD Test</p>
                        </TooltipContent>
                      )}
                    </Tooltip>
                  </TooltipProvider>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
      </Sidebar>
      <main className="flex-1">
        <div className="border-b px-4 py-2 flex items-center gap-4">
          <SidebarTrigger />
          <div className="flex-1">
            <h2 className="text-lg font-semibold">{getPageTitle()}</h2>
          </div>
        </div>
        {renderContent()}
      </main>
    </>
  );
};

const AppLayout: React.FC = () => {
  return (
    <SidebarProvider defaultOpen={true}>
      <AppContent />
    </SidebarProvider>
  );
};

export default AppLayout;
