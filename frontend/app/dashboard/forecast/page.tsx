import ForecastView from "../../../components/forecast-view";

export default function ForecastPage() {
  return <ForecastPageClient />;
}

function ForecastPageClient() {
  return <ForecastViewBridge />;
}

function ForecastViewBridge() {
  return <ForecastViewWithState />;
}

// Keep the route server-compatible while the workspace state remains client-owned.
import ForecastViewWithState from "../../../components/forecast-route-view";
