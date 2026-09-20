import { Routes, Route } from 'react-router-dom';
import VisitorLayout from '../layouts/VisitorLayout';
import StaffLayout from '../layouts/StaffLayout';
import RoleGuard from '../components/RoleGuard';

import HomePage from '../pages/visitor/HomePage';
import CollectionsPage from '../pages/visitor/CollectionsPage';
import CollectionItemPage from '../pages/visitor/CollectionItemPage';
import EventsPage from '../pages/visitor/EventsPage';
import EventDetailPage from '../pages/visitor/EventDetailPage';
import SignInPage from '../pages/SignInPage';
import PlaceholderPage from '../pages/PlaceholderPage';
import NotFoundPage from '../pages/NotFoundPage';

import StaffDashboard from '../pages/staff/StaffDashboard';
import StaffEventsPage from '../pages/staff/StaffEventsPage';
import OpeningHoursPage from '../pages/staff/OpeningHoursPage';

/**
 * Three route trees, one per audience.
 *
 *   public  — anyone, inside VisitorLayout
 *   /staff  — staff and admin, inside StaffLayout
 *   /admin  — admin only, inside StaffLayout
 *
 * The staff and admin trees are separate <Route> groups with different
 * `allow` lists rather than one tree with per-page checks. One place to read,
 * one place to get wrong, and it lines up with the role-permission matrix in
 * the API contract so Rock can test them against each other.
 */
export default function AppRoutes() {
  return (
    <Routes>
      {/* ---------- public ---------- */}
      <Route element={<VisitorLayout />}>
        <Route index element={<HomePage />} />
        <Route path="signin" element={<SignInPage />} />

        <Route path="visit" element={<PlaceholderPage title="Plan your visit" />} />

        <Route path="exhibitions" element={<PlaceholderPage title="Exhibitions" />} />
        <Route path="exhibitions/:slug" element={<PlaceholderPage title="Exhibition" />} />

        <Route path="collections" element={<CollectionsPage />} />
        <Route path="collections/:slug" element={<CollectionItemPage />} />

        <Route path="events" element={<EventsPage />} />
        <Route path="events/:slug" element={<EventDetailPage />} />

        <Route path="membership" element={<PlaceholderPage title="Membership" />} />
        <Route path="book" element={<PlaceholderPage title="Book tickets" />} />

        {/* Members only — a staff account has no membership to show. */}
        <Route element={<RoleGuard allow={['member']} />}>
          <Route path="account" element={<PlaceholderPage title="My membership" />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>

      {/* ---------- staff workspace ---------- */}
      <Route element={<RoleGuard allow={['staff', 'admin']} />}>
        <Route path="/staff" element={<StaffLayout />}>
          <Route index element={<StaffDashboard />} />
          <Route path="content" element={<PlaceholderPage title="Exhibitions & collections" />} />
          <Route path="events" element={<StaffEventsPage />} />
          <Route path="hours" element={<OpeningHoursPage />} />
          <Route path="bookings" element={<PlaceholderPage title="Bookings & check-in" />} />
        </Route>
      </Route>

      {/* ---------- administration ---------- */}
      <Route element={<RoleGuard allow={['admin']} />}>
        <Route path="/admin" element={<StaffLayout />}>
          <Route path="members" element={<PlaceholderPage title="Members" />} />
          <Route path="accounts" element={<PlaceholderPage title="Staff accounts & roles" />} />
          <Route path="activity" element={<PlaceholderPage title="Activity log" />} />
        </Route>
      </Route>
    </Routes>
  );
}
