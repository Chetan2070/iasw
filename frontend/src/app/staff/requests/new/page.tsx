import RequestForm from "@/components/staff/RequestForm";

export default function NewRequestPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">New Request</h1>
        <p className="text-gray-600 mt-1">
          Submit a new customer account change request
        </p>
      </div>

      <RequestForm />
    </div>
  );
}
