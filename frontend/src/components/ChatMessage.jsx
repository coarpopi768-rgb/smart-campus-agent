export default function ChatMessage({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div className={'flex ' + (isUser ? 'justify-end' : 'justify-start') + ' mb-4'}>
      <div className={
        'max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ' +
        (isUser
          ? 'bg-blue-600 text-white rounded-br-md'
          : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-md')
      }>
        <div className="whitespace-pre-wrap">{msg.content}</div>
      </div>
    </div>
  );
}
