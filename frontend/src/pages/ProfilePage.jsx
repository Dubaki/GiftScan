import { useTelegram } from "../hooks/useTelegram";

export default function ProfilePage() {
  const { user } = useTelegram();

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Profile</h1>
      {user ? (
        <div className="space-y-2 text-sm">
          <p>
            <span className="text-gray-400">User: </span>
            {user.first_name} {user.last_name ?? ""}
          </p>
          <p>
            <span className="text-gray-400">ID: </span>
            {user.id}
          </p>
          {user.username && (
            <p>
              <span className="text-gray-400">Username: </span>@{user.username}
            </p>
          )}
        </div>
      ) : (
        <p className="text-gray-500 text-sm">Open in Telegram to see your profile.</p>
      )}
    </div>
  );
}
