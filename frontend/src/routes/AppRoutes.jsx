import { Routes, Route } from 'react-router-dom';
import VisitorLayout from '../layouts/VisitorLayout';
import HomePage from '../pages/visitor/HomePage';
import CollectionsPage from '../pages/visitor/CollectionsPage';
import CollectionItemPage from '../pages/visitor/CollectionItemPage';
import EventsPage from '../pages/visitor/EventsPage';
import EventDetailPage from '../pages/visitor/EventDetailPage';
import PlaceholderPage from '../pages/PlaceholderPage';
import NotFoundPage from '../pages/NotFoundPage';

/**
 * Every visitor route lives here. The five MVP functional areas agreed with
 * the client are: home, collection search, events, member portal, ticket
 * booking. Staff and admin routes are added in a separate <Route> tree later,
 * behind a role guard — do not nest them under VisitorLayout.
 */
export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<VisitorLayout />}>
        <Route index element={<HomePage />} />

        <Route path="visit" element={<PlaceholderPage title="Plan your visit" />} />

        <Route path="exhibitions" element={<PlaceholderPage title="Exhibitions" />} />
        <Route path="exhibitions/:slug" element={<PlaceholderPage title="Exhibition" />} />

        <Route path="collections" element={<CollectionsPage />} />
        <Route path="collections/:slug" element={<CollectionItemPage />} />

        <Route path="events" element={<EventsPage />} />
        <Route path="events/:slug" element={<EventDetailPage />} />

        <Route path="membership" element={<PlaceholderPage title="Membership" />} />

        <Route path="book" element={<PlaceholderPage title="Book tickets" />} />

        <Route path="account" element={<PlaceholderPage title="My membership" />} />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
