import { Route, Routes } from "react-router";

import Layout from "./components/Layout";
import AboutPage from "./pages/AboutPage";
import MapPage from "./pages/MapPage";
import NotFoundPage from "./pages/NotFoundPage";
import ResultsPage from "./pages/ResultsPage";
import SearchPage from "./pages/SearchPage";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<SearchPage />} />
        <Route path="flight/:number/:date" element={<ResultsPage />} />
        <Route path="map" element={<MapPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

export default App;
