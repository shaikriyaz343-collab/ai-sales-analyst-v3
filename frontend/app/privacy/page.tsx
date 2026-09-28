import LegalPage from "../../components/legal-page";

export default function PrivacyPage() {
  return (
    <LegalPage
      label="PRIVACY POLICY"
      title="Avenlytics Privacy Policy"
      intro="This Privacy Policy explains how Avenlytics collects, uses, stores, and shares information when you use the Avenlytics AI Sales Analyst."
      sections={[
        { title:"1. Information we collect", items:[
          "Account information such as your name, email address, organization name, and login credentials.",
          "Sales files and data you upload, together with the analysis, reports, monitoring rules, and saved intelligence generated from that data.",
          "Subscription and billing metadata such as Paddle customer and subscription identifiers. Payment card details are handled by Paddle rather than stored by Avenlytics.",
          "Technical information such as IP address, request identifiers, browser information, service logs, security events, and reliability telemetry."
        ]},
        { title:"2. How we use information", items:[
          "Provide and secure the Avenlytics service and authenticate users.",
          "Process uploaded sales data to calculate validated metrics and generate requested analysis and reports.",
          "Enforce organization access, usage limits, and subscription state.",
          "Process billing events and reconcile subscription state with our payment provider.",
          "Troubleshoot failures, prevent abuse, investigate security incidents, and meet legal obligations."
        ]},
        { title:"3. Customer sales data", paragraphs:[
          "You retain your rights in the sales data and files you submit. Avenlytics uses that data to provide the requested analysis and related product features.",
          "You are responsible for having the permissions and lawful basis needed to upload and process the data you provide, including personal information contained in sales exports."
        ]},
        { title:"4. Service providers", paragraphs:[
          "Current production infrastructure uses Railway for application and database hosting, Cloudflare R2-compatible object storage for durable uploaded-data storage, and Paddle for billing and payment processing.",
          "Payment processing is subject to Paddle's own terms and privacy notice."
        ]},
        { title:"5. Cookies and technical data", paragraphs:[
          "Avenlytics uses an essential session cookie to keep you signed in and secure authenticated requests. We may also use limited technical telemetry for security and reliability."
        ]},
        { title:"6. Retention and deletion", paragraphs:[
          "We retain information for as long as needed to provide the service and for legitimate operational, security, accounting, dispute-resolution, and legal purposes.",
          "You may contact us about deletion of your account or data. Requests may be subject to lawful retention requirements and active billing, dispute, security, or backup obligations."
        ]},
        { title:"7. Your rights", paragraphs:[
          "Depending on your location and applicable law, you may have rights to access, correct, delete, restrict, object to, or obtain a copy of your personal information. Contact us using the email below. We may verify your identity before completing a request."
        ]},
        { title:"8. Contact and updates", paragraphs:[
          "We may update this policy as the product, providers, or applicable law changes. The current version will always be posted on this page."
        ]}
      ]}
    />
  );
}
