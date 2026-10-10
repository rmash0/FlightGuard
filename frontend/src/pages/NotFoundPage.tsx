import { Link } from "react-router";

function NotFoundPage() {
  return (
    <section>
      <h1>This page flew off course</h1>
      <p>
        <Link to="/">Back to search</Link>
      </p>
    </section>
  );
}

export default NotFoundPage;
