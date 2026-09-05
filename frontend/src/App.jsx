import { useEffect, useState } from "react";
import axios from "axios";
import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  CircleDollarSign,
  ShieldCheck,
  TrendingUp,
  XCircle,
  Sparkles,
  Play,
  Loader2,
} from "lucide-react";

const API = "http://127.0.0.1:8000";

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);

  const [aiResult, setAiResult] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [executeLoading, setExecuteLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState("");
  const [auditLogs, setAuditLogs] = useState([]);

  const loadData = async () => {
    try {
      const [
  dashboardResponse,
  paymentsResponse,
  auditResponse,
] = await Promise.all([
  axios.get(`${API}/recovery/dashboard`),
  axios.get(`${API}/payments/`),
  axios.get(`${API}/recovery/audit`),
]);

      setDashboard(dashboardResponse.data);
      setPayments(paymentsResponse.data);
      setAuditLogs(auditResponse.data);
    } catch (error) {
      console.error("Failed to load RecoverAI data:", error);
    } finally {
      setLoading(false);
    }
  };

  const failedPayments = payments.filter(
  (payment) => payment.status === "FAILED"
);

const recoveredPayments = payments.filter(
  (payment) => payment.status === "RECOVERED"
);

const failedAmount = failedPayments.reduce(
  (sum, payment) => sum + Number(payment.amount),
  0
);

const recoveredAmount = recoveredPayments.reduce(
  (sum, payment) => sum + Number(payment.amount),
  0
);

const totalPaymentVolume = failedAmount + recoveredAmount;

const failedPercentage =
  totalPaymentVolume > 0
    ? (failedAmount / totalPaymentVolume) * 100
    : 0;

const recoveredPercentage =
  totalPaymentVolume > 0
    ? (recoveredAmount / totalPaymentVolume) * 100
    : 0;

const failureReasons = {};

payments
  .filter((payment) => payment.status === "FAILED")
  .forEach((payment) => {
    const reason = payment.failure_reason || "UNKNOWN";

    failureReasons[reason] =
      (failureReasons[reason] || 0) + 1;
  });

const topFailureReasons = Object.entries(failureReasons)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 5);

  useEffect(() => {
    loadData();
  }, []);

  const formatINR = (amount) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amount || 0);

  const getStatusIcon = (status) => {
    if (status === "RECOVERED") {
      return <CheckCircle2 size={17} />;
    }

    if (status === "FAILED") {
      return <XCircle size={17} />;
    }

    return <AlertTriangle size={17} />;
  };

  const analyzeWithAI = async (paymentId) => {
    setAiLoading(true);
    setAiResult(null);
    setActionMessage("");

    try {
      const response = await axios.post(
        `${API}/recovery/ai-decide/${paymentId}`
      );

      setAiResult(response.data);
    } catch (error) {
      console.error("AI analysis failed:", error);

      setActionMessage(
        error.response?.data?.detail ||
          "AI analysis failed. Please try again."
      );
    } finally {
      setAiLoading(false);
    }
  };

  const executeRecovery = async (paymentId) => {
    setExecuteLoading(true);
    setActionMessage("");

    try {
      const response = await axios.post(
        `${API}/recovery/ai-execute/${paymentId}`
      );

      if (response.data.result === "SUCCESS") {
        setActionMessage(
          `Recovery successful — ${formatINR(
            response.data.amount_recovered
          )} recovered.`
        );
      } else {
        setActionMessage(
          `Recovery not executed — ${response.data.final_action}.`
        );
      }

      await loadData();

      // Re-analyze after execution only if needed
      setAiResult(null);
    } catch (error) {
      console.error("Recovery execution failed:", error);

      setActionMessage(
        error.response?.data?.detail ||
          "Recovery execution failed. Please try again."
      );
    } finally {
      setExecuteLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <Brain size={22} />
          </div>

          <div>
            <h1>RecoverAI</h1>
            <p>AI-Powered Revenue Recovery</p>
          </div>
        </div>

        <div className="system-status">
          <span className="status-dot"></span>
          System Online
        </div>
      </header>

      <main className="container">
        <section className="hero">
          <div>
            <p className="eyebrow">REVENUE RECOVERY AGENT</p>

            <h2>
              Find revenue at risk.
              <br />
              <span>Recover it intelligently.</span>
            </h2>

            <p className="hero-text">
              RecoverAI combines AI reasoning with deterministic policy
              controls to recover failed payments safely.
            </p>
          </div>

          <div className="hero-badge">
            <ShieldCheck size={22} />

            <div>
              <strong>AI + Policy Guardrails</strong>
              <small>AI recommends. Policy decides.</small>
            </div>
          </div>
        </section>

        {loading ? (
          <div className="loading">Loading RecoverAI...</div>
        ) : (
          <>
            {/* METRICS */}

            <section className="metrics">
              <MetricCard
                icon={<CircleDollarSign />}
                label="Revenue at Risk"
                value={formatINR(dashboard?.revenue_at_risk)}
              />

              <MetricCard
                icon={<TrendingUp />}
                label="Revenue Recovered"
                value={formatINR(dashboard?.revenue_recovered)}
              />

              <MetricCard
                icon={<CheckCircle2 />}
                label="Recovery Rate"
                value={`${dashboard?.recovery_rate_percent || 0}%`}
              />

              <MetricCard
                icon={<Brain />}
                label="Successful Recoveries"
                value={dashboard?.successful_recoveries || 0}
              />
            </section>

            {/* PAYMENT MONITOR */}

            <section className="panel">
              <div className="panel-header">
                <div>
                  <h3>Payment Recovery Monitor</h3>
                  <p>
                    Analyze failed payments and recover revenue with AI
                  </p>
                </div>

                <button onClick={loadData}>Refresh</button>
              </div>

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Payment</th>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Failure Reason</th>
                      <th>Attempts</th>
                      <th>AI Recovery</th>
                    </tr>
                  </thead>

                  <tbody>
                    {payments.map((payment) => (
                      <tr key={payment.id}>
                        <td>
                          <strong>#{payment.id}</strong>
                        </td>

                        <td>
                          <strong>{formatINR(payment.amount)}</strong>
                        </td>

                        <td>
                          <span
                            className={`status ${
                              payment.status === "RECOVERED"
                                ? "success"
                                : "failed"
                            }`}
                          >
                            {getStatusIcon(payment.status)}
                            {payment.status}
                          </span>
                        </td>

                        <td>
                          {payment.failure_reason || "—"}
                        </td>

                        <td>{payment.attempt_count}</td>

                        <td>
                          {payment.status === "FAILED" ? (
                            <button
                              className="ai-button"
                              onClick={() =>
                                analyzeWithAI(payment.id)
                              }
                            >
                              <Sparkles size={15} />
                              Analyze with AI
                            </button>
                          ) : (
                            <span className="completed-label">
                              Recovery completed
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* AI ANALYSIS */}

            {(aiLoading || aiResult || actionMessage) && (
              <section className="ai-panel">
                <div className="ai-panel-header">
                  <div className="ai-title">
                    <div className="ai-main-icon">
                      <Sparkles size={20} />
                    </div>

                    <div>
                      <h3>AI Recovery Analysis</h3>
                      <p>
                        Gemini recommendation + deterministic policy
                      </p>
                    </div>
                  </div>

                  {aiResult && (
                    <span className="decision-badge">
                      {aiResult.final_decision?.decision}
                    </span>
                  )}
                </div>

                {aiLoading ? (
                  <div className="ai-loading">
                    <Loader2 className="spin" size={24} />
                    <div>
                      <strong>Gemini is analyzing...</strong>
                      <p>
                        Evaluating payment failure and customer history.
                      </p>
                    </div>
                  </div>
                ) : aiResult ? (
                  <>
                    <div className="ai-summary">
                      <div>
                        <span>Payment</span>
                        <strong>
                          #{aiResult.payment_id}
                        </strong>
                      </div>

                      <div>
                        <span>Amount</span>
                        <strong>
                          {formatINR(aiResult.amount)}
                        </strong>
                      </div>

                      <div>
                        <span>Failure</span>
                        <strong>
                          {aiResult.failure_reason}
                        </strong>
                      </div>
                    </div>

                    <div className="ai-grid">
                      {/* AI */}

                      <div className="decision-card ai-card">
                        <div className="decision-card-header">
                          <Brain size={18} />
                          <span>AI Recommendation</span>
                        </div>

                        <h4>
                          {aiResult.ai_analysis.recommended_action}
                        </h4>

                        <div className="risk-row">
                          <span>Risk</span>

                          <span
                            className={`risk ${aiResult.ai_analysis.risk_level.toLowerCase()}`}
                          >
                            {aiResult.ai_analysis.risk_level}
                          </span>
                        </div>

                        <div className="confidence">
                          <div className="confidence-header">
                            <span>Confidence</span>
                            <strong>
                              {Math.round(
                                aiResult.ai_analysis.confidence * 100
                              )}
                              %
                            </strong>
                          </div>

                          <div className="confidence-bar">
                            <div
                              style={{
                                width: `${
                                  aiResult.ai_analysis.confidence * 100
                                }%`,
                              }}
                            ></div>
                          </div>
                        </div>

                        <p className="reason">
                          {aiResult.ai_analysis.reason}
                        </p>

                        <div className="root-cause">
                          <strong>Root Cause</strong>
                          <p>
                            {aiResult.ai_analysis.root_cause}
                          </p>
                        </div>
                      </div>

                      {/* POLICY */}

                      <div className="decision-card policy-card">
                        <div className="decision-card-header">
                          <ShieldCheck size={18} />
                          <span>Policy Decision</span>
                        </div>

                        <h4>
                          {aiResult.policy_decision.action}
                        </h4>

                        <div className="policy-status">
                          {aiResult.policy_decision.eligible ? (
                            <>
                              <CheckCircle2 size={16} />
                              Recovery eligible
                            </>
                          ) : (
                            <>
                              <XCircle size={16} />
                              Recovery blocked
                            </>
                          )}
                        </div>

                        <p className="reason">
                          {aiResult.policy_decision.reason}
                        </p>
                      </div>

                      {/* FINAL */}

                      <div className="decision-card final-card">
                        <div className="decision-card-header">
                          <TrendingUp size={18} />
                          <span>Final Decision</span>
                        </div>

                        <h4>
                          {aiResult.final_decision.action}
                        </h4>

                        <div
                          className={`final-status ${
                            aiResult.final_decision.decision ===
                            "AI_POLICY_MATCH"
                              ? "match"
                              : "override"
                          }`}
                        >
                          {aiResult.final_decision.decision ===
                          "AI_POLICY_MATCH" ? (
                            <>
                              <CheckCircle2 size={16} />
                              AI + Policy Match
                            </>
                          ) : (
                            <>
                              <ShieldCheck size={16} />
                              Policy Override
                            </>
                          )}
                        </div>

                        <p className="reason">
                          {aiResult.final_decision.reason}
                        </p>

                        {aiResult.final_decision.action ===
                          "RETRY_PAYMENT" &&
                        aiResult.payment_id ? (
                          <button
                            className="execute-button"
                            disabled={executeLoading}
                            onClick={() =>
                              executeRecovery(
                                aiResult.payment_id
                              )
                            }
                          >
                            {executeLoading ? (
                              <>
                                <Loader2
                                  size={16}
                                  className="spin"
                                />
                                Executing...
                              </>
                            ) : (
                              <>
                                <Play size={16} />
                                Execute Recovery
                              </>
                            )}
                          </button>
                        ) : (
                          <div className="blocked-message">
                            <ShieldCheck size={16} />
                            Automatic execution blocked by policy
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                ) : null}

                {actionMessage && (
                  <div className="action-message">
                    <CheckCircle2 size={17} />
                    {actionMessage}
                  </div>
                )}
              </section>
            )}

<section className="audit-panel">
  <div className="panel-header">
    <div>
      <h3>Audit Trail</h3>
      <p>
        Complete history of AI decisions, policy overrides and recovery actions
      </p>
    </div>

    <span className="audit-count">
      {auditLogs.length} Events
    </span>
  </div>

  <div className="audit-list">
    {auditLogs.slice(0, 10).map((log) => (
      <div className="audit-item" key={log.id}>
        <div className="audit-icon">
          {log.event.includes("BLOCKED") ? (
            <ShieldCheck size={17} />
          ) : log.event.includes("EXECUTED") ? (
            <CheckCircle2 size={17} />
          ) : (
            <Brain size={17} />
          )}
        </div>

        <div className="audit-content">
          <div className="audit-top">
            <strong>
              Payment #{log.payment_id}
            </strong>

            <span className="audit-time">
              {new Date(log.timestamp).toLocaleString("en-IN")}
            </span>
          </div>

          <div className="audit-event">
            {log.event.replaceAll("_", " ")}
          </div>

          <p>{log.description}</p>
        </div>
      </div>
    ))}
  </div>
</section>

<section className="analytics-grid">

  <div className="analytics-card">

    <div className="analytics-header">
      <div>
        <h3>Recovery Performance</h3>
        <p>Revenue distribution across payment outcomes</p>
      </div>
    </div>

    <div className="performance-chart">

      <div className="chart-row">
        <div className="chart-label">
          <span>Recovered</span>
          <strong>{formatINR(recoveredAmount)}</strong>
        </div>

        <div className="bar-track">
          <div
            className="bar recovered-bar"
            style={{
              width: `${recoveredPercentage}%`
            }}
          ></div>
        </div>

        <span className="chart-percent">
          {Math.round(recoveredPercentage)}%
        </span>
      </div>


      <div className="chart-row">
        <div className="chart-label">
          <span>Still at Risk</span>
          <strong>{formatINR(failedAmount)}</strong>
        </div>

        <div className="bar-track">
          <div
            className="bar risk-bar"
            style={{
              width: `${failedPercentage}%`
            }}
          ></div>
        </div>

        <span className="chart-percent">
          {Math.round(failedPercentage)}%
        </span>
      </div>

    </div>

    <div className="analytics-total">
      <span>Total Recovery Opportunity</span>
      <strong>{formatINR(totalPaymentVolume)}</strong>
    </div>

  </div>


  <div className="analytics-card">

    <div className="analytics-header">
      <div>
        <h3>Failure Analysis</h3>
        <p>Most common payment failure reasons</p>
      </div>
    </div>

    <div className="failure-list">

      {topFailureReasons.length === 0 ? (
        <p className="empty-state">
          No failed payments
        </p>
      ) : (
        topFailureReasons.map(([reason, count]) => {

          const percentage =
            failedPayments.length > 0
              ? (count / failedPayments.length) * 100
              : 0;

          return (
            <div
              className="failure-row"
              key={reason}
            >

              <div className="failure-info">
                <span>{reason}</span>
                <strong>{count}</strong>
              </div>

              <div className="failure-track">
                <div
                  className="failure-bar"
                  style={{
                    width: `${percentage}%`
                  }}
                ></div>
              </div>

            </div>
          );
        })
      )}

    </div>

  </div>

</section>
            {/* PRODUCT FEATURES */}

            <section className="bottom-grid">
              <div className="info-card">
                <div className="card-icon">
                  <Brain />
                </div>

                <h3>AI Decisioning</h3>

                <p>
                  Gemini analyzes payment context, failure reason and
                  customer history to recommend the safest recovery action.
                </p>
              </div>

              <div className="info-card">
                <div className="card-icon">
                  <ShieldCheck />
                </div>

                <h3>Policy Guardrails</h3>

                <p>
                  Deterministic rules remain the final authority. Unsafe
                  recommendations are blocked or overridden automatically.
                </p>
              </div>

              <div className="info-card">
                <div className="card-icon">
                  <TrendingUp />
                </div>

                <h3>Measured Recovery</h3>

                <p>
                  Every recovery action produces an outcome and audit trail,
                  making recovered revenue measurable.
                </p>
              </div>
            </section>
          </>
        )}
      </main>

      <footer>
        RecoverAI · AI Revenue Recovery Agent · Demo Environment
      </footer>
    </div>
  );
}

function MetricCard({ icon, label, value }) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>

      <div>
        <p>{label}</p>
        <h3>{value}</h3>
      </div>
    </div>
  );
}

export default App;