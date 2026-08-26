import WorkspaceView from "../../../components/workspace-view";

export default function DashboardWorkspacePage({ params }: { params: Promise<{ workspace: string }> }) {
  return <WorkspaceView params={params} />;
}
