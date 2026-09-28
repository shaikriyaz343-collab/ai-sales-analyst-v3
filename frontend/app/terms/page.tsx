import LegalPage from "../../components/legal-page";

export default function TermsPage() {
  return (
    <LegalPage
      label="TERMS & CONDITIONS"
      title="Avenlytics Terms of Service"
      intro="These Terms govern your access to and use of Avenlytics, an AI Sales Analyst that helps sales teams analyze the sales data they provide, investigate validated revenue signals, generate reports, and manage evidence-backed monitoring."
      sections={[
        {
          title: "1. Agreement and scope",
          paragraphs: [
            "By creating an Avenlytics account or using the service, you agree to these Terms. If you use Avenlytics for an organization, you confirm that you are authorized to accept these Terms on that organization's behalf.",
            "Avenlytics is an analyst layer over customer-provided sales data. It is not a system of record, CRM replacement, accounting system, or source of independent market facts.",
          ],
        },
        {
          title: "2. Plans, trial, and billing",
          paragraphs: [
            "Avenlytics currently offers a 14-day trial and paid monthly plans. Current public pricing is Starter at USD 49 per month and Growth at USD 149 per month. Pricing shown at checkout is the price applicable to the transaction.",
            "Subscriptions renew according to the billing terms presented at checkout until canceled. Cancellation generally takes effect at the end of the current billing period and prevents future recurring charges, subject to applicable law and the payment provider's terms.",
            "Payments are processed through Paddle, which acts as the authorized reseller / Merchant of Record for applicable transactions. Your checkout and payment transaction are also subject to Paddle's Buyer Terms and Refund Policy.",
          ],
        },
        {
          title: "3. Accounts and security",
          items: [
            "Provide accurate account and organization information and keep it reasonably current.",
            "Keep your credentials confidential and promptly notify us if you believe your account has been accessed without authorization.",
            "You are responsible for activity performed through your account, except where applicable law provides otherwise.",
          ],
        },
        {
          title: "4. Customer data",
          paragraphs: [
            "You retain your rights in the sales data, files, and other content you submit to Avenlytics. You grant Avenlytics the limited rights needed to host, process, analyze, store, and return that content to you as part of the service.",
            "You are responsible for having the rights and permissions needed to upload and process the data you provide, including any personal data contained in sales exports.",
          ],
        },
        {
          title: "5. Analytics and AI limitations",
          paragraphs: [
            "Avenlytics is designed to calculate metrics from validated fields in the data you provide. When the available evidence does not support an answer, the service may return a limitation rather than infer or invent a result.",
            "Outputs are decision-support information and should be reviewed in the context of your own business. You remain responsible for business, financial, legal, employment, credit, and other consequential decisions made using the service.",
          ],
        },
        {
          title: "6. Acceptable use",
          paragraphs: ["You may not use Avenlytics to:"],
          items: [
            "violate applicable law or another person's rights;",
            "upload malicious code or attempt to disrupt, probe, or bypass service security;",
            "reverse engineer or copy the service except where applicable law permits it;",
            "use the service to create or distribute unlawful, fraudulent, or abusive content.",
          ],
        },
        {
          title: "7. Availability and changes",
          paragraphs: [
            "We may improve, change, suspend, or discontinue features over time. We will make reasonable efforts to keep the service available, but we do not guarantee uninterrupted or error-free operation.",
            "We may update these Terms when needed for legal, operational, or product reasons. The updated version will be posted on this page with a new effective date.",
          ],
        },
        {
          title: "8. Intellectual property",
          paragraphs: [
            "Avenlytics and its software, interface, branding, and underlying technology are owned by or licensed to Avenlytics. Except for the rights expressly granted in these Terms, no ownership rights are transferred to you.",
          ],
        },
        {
          title: "9. Suspension and termination",
          paragraphs: [
            "We may suspend or terminate access where reasonably necessary to address security risks, fraud, unlawful use, non-payment, or material breach of these Terms. You may stop using the service at any time and cancel a subscription through the available billing controls.",
          ],
        },
        {
          title: "10. Contact",
          paragraphs: [
            "For support, billing questions, privacy requests, or questions about these Terms, contact Avenlytics at the support email shown below.",
          ],
        },
      ]}
    />
  );
}
