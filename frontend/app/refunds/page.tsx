import LegalPage from "../../components/legal-page";

export default function RefundsPage() {
  return (
    <LegalPage
      label="REFUND POLICY"
      title="Avenlytics Refund Policy"
      intro="Avenlytics subscriptions and payments are processed through Paddle. This policy explains how cancellations and refund requests are handled alongside Paddle's current Buyer Terms and Refund Policy."
      sections={[
        { title:"1. Payment processor", paragraphs:[
          "Paddle acts as the authorized reseller / Merchant of Record for applicable Avenlytics transactions. Paddle processes payment and refund requests for those transactions under its policies and applicable law.",
          "Paddle's current Buyer Terms and Refund Policy apply to the transaction, including any mandatory consumer rights."
        ]},
        { title:"2. Subscription cancellation", paragraphs:[
          "You can cancel an Avenlytics subscription through the Paddle Customer Portal when it is available from the Avenlytics billing area.",
          "Cancellation generally takes effect at the end of the current billing period and prevents future recurring charges. Cancellation alone does not automatically create a refund for a prior billing period."
        ]},
        { title:"3. Refund requests", paragraphs:[
          "Use the refund or support route provided by Paddle in your transaction receipt, customer portal, or Paddle support site. You may also contact Avenlytics support and we will direct you to the appropriate Paddle process.",
          "Applicable statutory withdrawal and refund rights are not excluded by this policy."
        ]},
        { title:"4. Trial period", paragraphs:[
          "Avenlytics currently offers a 14-day trial. Trial access and any conversion to a paid subscription are governed by the pricing and checkout terms shown when you start or upgrade your subscription."
        ]},
        { title:"5. Access after cancellation or refund", paragraphs:[
          "When a refund is approved, access to the applicable paid product may end according to the payment provider's refund process. When a subscription is canceled without a refund, access generally continues until the end of the paid billing period unless the account is suspended for another reason."
        ]}
      ]}
    />
  );
}
