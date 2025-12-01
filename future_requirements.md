Roadmap for Expanding the Streamlit MES Application

The current Streamlit app began as a digital Andon & downtime tracker and has grown to include basic MES features. It already provides an Operator Panel for logging downtime/scrap with timers, a Supervisor Dashboard with performance metrics and Pareto charts, a Maintenance View for tracking and resolving downtime tickets, and an Admin Config for master data management
GitHub
GitHub
. The initial scope was an MVP for a single-site, tablet-friendly tool with no user authentication and a local SQLite database
GitHub
. To evolve this into a full-blown Manufacturing Execution System (MES) while preserving Streamlit’s simplicity, we propose the following roadmap of new features and architectural enhancements. The roadmap is split into incremental improvements (new pages/features) and more “exponential” changes (architecture, integrations), along with key concerns and mitigation strategies.

Phase 1: Incremental Feature Additions (Next 1-3 Months)

In the short term, add new pages and modules to cover missing MES functionality while sticking to Streamlit’s multipage structure:

Production Scheduling & Work Orders – Expand the current production management by introducing a Scheduling/Work Order page. This feature would let supervisors plan and dispatch work orders to lines, track progress, and assign targets. The data model already includes a work_orders table; integrating it more fully (e.g. listing active orders, marking completion) bridges a key MES gap
GitHub
. Concern: This adds complexity in tracking order status. Mitigation: Keep the UI simple (e.g. a table of orders with status), and consider loading orders from an ERP system later on via an integration
GitHub
 (for now, allow CSV import or manual entry to maintain simplicity).

Quality Management Enhancements – Build on the scrap logging to include Quality Inspection and Defect Tracking. For example, a Quality page could record inspection results, defect types, and corrective actions. This aligns with full MES capabilities in capturing quality issues beyond just scrap counts. Concern: More data input could overwhelm operators. Mitigation: Design the UI with minimal input requirements (predefined defect codes, simple pass/fail toggles) and perhaps limit this to quality staff users. Leverage the existing quality_reasons and quality_events schema to categorize defects
GitHub
GitHub
. We can later generate Pareto charts of defects or first-pass yield metrics to support lean initiatives.

Expanded Dashboard & Reporting – Add new analytics pages for historical trends and lean metrics. Currently, the supervisor view shows shift-level performance; a full MES should provide multi-shift or multi-day analysis (e.g. trends over weeks, months). A Reports page can offer interactive filters (date ranges, lines, machines) and charts for downtime by category over time, production rates, and quality trends. In the MVP, catering to a Process Engineer persona was noted as a later goal (historical Pareto over days/weeks)
GitHub
. Concern: Large data volumes over time could slow down Streamlit. Mitigation: Use Pandas/Altair efficiently for aggregation and limit default date ranges. For simplicity, start with coarse summaries (weekly totals, etc.), and only load detailed data on demand. This keeps the app responsive while offering richer insight.

OEE Calculation – Introduce Overall Equipment Effectiveness metrics, combining availability, performance, and quality. The groundwork is largely in place (downtime captures availability losses, scrap captures quality losses); what’s missing is performance (ideal cycle vs actual output). We can add a field for ideal cycle time or standard rate per machine and compute performance % vs standard. A new OEE section on the dashboard or a dedicated OEE page would show availability, performance, quality percentages and the overall OEE. The initial design explicitly aimed to allow extending to OEE later
GitHub
. Concern: Accuracy of OEE requires reliable standard rates and runtime data. Mitigation: Start with simple estimates (e.g. use target vs actual production from work orders as a proxy for performance). As IoT integration improves actual runtime data, refine the calculation. Keep the UI straightforward – perhaps a single OEE percentage dial or bar, with breakdowns on hover or in a tooltip to avoid clutter.

User Authentication & Roles – Although not in the MVP, as more features are added it may be wise to implement basic authentication with role-based access (operators vs supervisors vs admins). This can be done incrementally using Streamlit’s authentication integrations or a simple login page. Concern: Adding auth could complicate the user flow. Mitigation: Use a lightweight approach (e.g. environment-based password or a third-party OAuth) so that daily operator workflow (which currently just selects their name) remains nearly as simple. Role-based filtering of pages (Streamlit’s multipage can hide pages not relevant to a role) will keep the UI uncluttered for each user type.

Phase 2: System Integration & IoT (3-6 Months)

Once the app covers core MES functions, the next step is integrating with external systems and real-time data sources:

IoT Data Integration (MQTT) – Incorporate machine data via IoT to automate data capture. For example, use an MQTT broker to receive signals from machines (e.g. machine state changes, cycle counts). A background thread or separate service can subscribe to topics and update the Streamlit app’s database or state in real-time
discuss.streamlit.io
. In practice, one could run an MQTT client (using Paho MQTT) in a non-blocking mode (e.g. client.loop_start() in a thread) that writes incoming events to the SQLite (or a cache). The Streamlit app can then periodically query for new data or use st.experimental_rerun() triggers when new events arrive. Concern: Streamlit’s reactive framework doesn’t natively support push updates from background threads. As community discussions show, naive approaches (like calling st.write in an MQTT callback) won’t update the UI
discuss.streamlit.io
. Mitigation: Use a polling strategy or Streamlit’s session state. For instance, maintain a timestamp or counter that the UI checks (e.g. using st.experimental_singleton or a cached data function) and triggers a rerun when updated. This ensures UI updates remain in the Streamlit event loop. Despite some complexity under the hood, the UI can stay simple – e.g. a live status indicator that turns red when a machine sends a downtime signal, or an auto-updating production counter.

ERP/System Integration – Connect the MES app with higher-level systems like ERP for master data and production orders. For discrete manufacturing, this means importing work orders, BOMs or operation lists from an ERP so that scheduling and tracking are in sync. In the MVP, work orders were manually seeded, with a note to “later load from ERP”
GitHub
. We can implement this via scheduled CSV imports or direct database/API integration. Concern: Integrations add complexity and potential errors (data mismatches, connectivity issues). Mitigation: Phase the integration gradually – start by exporting reports to CSV for manual upload to ERP (or vice versa), then move to a read-only integration (pull data from ERP to display in Streamlit), and finally a two-way sync if needed. By staging it, the core app remains stable. Use clear data validation and allow fallbacks (e.g. if ERP is down, allow manual input).

Database & Concurrency Upgrade – As usage grows (more data, more concurrent users or devices), evaluate moving from the local SQLite to a more robust database (e.g. PostgreSQL or a cloud DB). The initial design acknowledged that SQLite is fine for a small-scale MVP, but a cloud/Postgres option is a future consideration
GitHub
. Migrating the data layer would allow multiple app instances or threads to read/write without the locking issues of SQLite. Concern: Migration and increased complexity in deployment (running a DB server) could undermine the “simple setup” ethos. Mitigation: Keep the migration optional/configurable. For single-factory deployments that prefer simplicity, they can continue with SQLite. Provide migration scripts so that switching to Postgres is straightforward when needed (e.g. if the app becomes mission-critical with many users). This way the default experience stays simple, but the architecture can scale when the time comes.

Advanced Lean Tools – In parallel, consider adding features for Lean management and continuous improvement. For example, a module for tracking Kaizen ideas or actions (operators or supervisors can submit improvement suggestions and track their implementation), or a Kanban board for visualizing work in progress if applicable. These can start as simple forms or tables within Streamlit. Concern: These features, while useful, could clutter the app if not designed well. Mitigation: If implemented, isolate them on separate pages (e.g. an “Improvement Ideas” page) and use Streamlit’s navigation to keep them out of the way unless needed. This maintains the clean experience for core tasks (operators logging issues, etc.). Lean tools should complement the data the app is already collecting (e.g. highlighting top downtime causes to focus Kaizen efforts), not create an entirely separate workflow.

Phase 3: Architectural Evolution (6-12+ Months)

As the application matures into a full MES and user demands grow, plan for more fundamental architectural enhancements that go beyond Streamlit’s out-of-the-box capabilities:

Modular Backend Services – If the Streamlit app starts to hit limits (for example, complex calculations slowing down page loads or difficulty handling concurrent IoT events), consider refactoring into a multi-tier architecture. In this model, a backend service (in FastAPI, Flask, or Node, etc.) would handle heavy lifting – e.g. an API for data ingestion from machines, or running long computations – and the Streamlit front-end would query this API. This preserves Streamlit for UI simplicity, but offloads processing. Issue: This is a significant change (essentially turning the single-app into a distributed system). Abatement: Only take this step if needed – i.e. monitor performance and maintainability. Streamlit’s simplicity is a strength; leverage it as long as feasible by using tools like st.cache_data or efficient Pandas instead of prematurely splitting the app. If splitting becomes necessary, do it incrementally (maybe start by moving just the IoT listener to a separate process that writes to the DB, which we already plan in Phase 2).

Scalability and Multi-Site Support – To truly be a “full MES,” the system might expand to multiple production sites or a larger user base. This could involve deploying the app on the cloud with proper security, allowing remote access to dashboards, and segregating data by site. Issue: Multi-site brings data complexity and potential performance issues with a lot more data. Abatement: Introduce site filters in the UI and partition data by site in the database. Use caching and indices in the DB for performance. Also, implement more robust user management (distinct logins per site or per role) if not done already. This ensures as we scale up, the user experience remains smooth and relevant (each user sees only their site’s data, etc.).

Enterprise Features (Long-term) – In the long run, consider features that large-scale MES solutions have, such as traceability (tracking lots/serials through the production chain), digital work instructions (delivering step-by-step instructions or drawings to operators), and predictive analytics (e.g. predicting machine failures or quality issues with AI). These are “exponential” additions that likely require new frameworks or heavy integrations (e.g. connecting to PLM systems for drawings, or using ML libraries for predictions). Issue: These go beyond the original scope and could complicate the app significantly. Abatement: Tackle them only if there is clear value and resourcing. If pursued, isolate each into its own service or module to keep the core app from becoming monolithic. For example, a separate microservice could handle a ML model for prediction and expose results to Streamlit via an API, rather than embedding complex ML code directly in the Streamlit script.

Maintaining Streamlit Simplicity Throughout

A guiding principle in this roadmap is to preserve the ease-of-use and rapid development benefits of Streamlit, even as the application grows:

Minimal and Intuitive UI: Each new feature should have a dedicated, simple interface (leveraging Streamlit’s pages/tabs). Avoid cramming too much into one page. For instance, operators should still see a clean panel with just the few actions they need (downtime, scrap entry). New complex features (scheduling, analytics) are kept to other pages for supervisors/engineers, so the basic screens remain uncluttered.

Incremental Complexity: Introduce complexity under-the-hood gradually. We start by adding pages using the same patterns (forms, buttons, caching). When moving to more complex integrations (IoT, external DB), we do so in a way that is transparent to the user. E.g., an operator might not even realize that a machine’s downtime was auto-logged via MQTT – they simply see the event appear on their screen. Internally it required an MQTT client and DB update, but externally the interface is the same or even simpler (less manual input).

Refactoring and Modular Code: As features grow, continuously refactor the codebase to keep it manageable. Use the modular design already in place (separate db.py helpers, pages for each section
GitHub
GitHub
). This keeps the “mental model” for developers simple, which in turn means faster iteration without breaking things – a huge advantage of Streamlit for prototyping. Document new modules thoroughly (similar to how the initial README and spec are detailed) so complexity is managed with clarity.

Performance Tuning vs. Over-Engineering: Before jumping to a complex architecture, try to optimize within Streamlit’s ecosystem. For example, use st.cache_data or st.cache_resource to avoid recomputing heavy queries, and utilize efficient Pandas operations for analytics. Streamlit can handle surprising amounts of logic if used wisely. Only when these techniques are insufficient do we escalate to externalizing components. This ensures we don’t lose Streamlit’s quick development cycle until absolutely necessary.

By following this roadmap, the application can steadily grow from a focused Andon/downtime tool into a comprehensive MES for discrete manufacturing. New capabilities like scheduling, richer production analytics, quality tracking, and IoT integration will fill the functional gaps. At the same time, careful architectural planning (database upgrades, optional microservices, integrations) will address scaling and complexity incrementally. Crucially, each step is designed to keep the user experience simple and intuitive, preserving the core strength of the Streamlit approach. With this balance, the app can evolve into a full MES that supports Andon alerts, maintenance, production management, lean initiatives, and beyond – all without overwhelming users or developers.