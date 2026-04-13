---
paths:
  - "**/*.dart"
---
# Dart Patterns

> This file extends [common/coding-style.md](../common/coding-style.md) with Dart-specific content.

## Flutter Widgets

Prefer stateless widgets; lift state up or use a state management solution:

```dart
class UserCard extends StatelessWidget {
  const UserCard({super.key, required this.user});
  final User user;

  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      title: Text(user.displayName),
      subtitle: Text(user.email),
    ),
  );
}
```

## Riverpod State Management

Use `@riverpod` annotations for providers:

```dart
@riverpod
Future<List<User>> userList(UserListRef ref) async {
  final repo = ref.watch(userRepositoryProvider);
  return repo.fetchAll();
}

// In widget:
final users = ref.watch(userListProvider);
return users.when(
  data:    (list) => UserListView(users: list),
  loading: () => const CircularProgressIndicator(),
  error:   (e, _) => Text('Error: $e'),
);
```

## Freezed Value Objects

Use `freezed` for immutable data classes with `copyWith`, equality, and pattern matching:

```dart
@freezed
class Order with _$Order {
  const factory Order({
    required String id,
    required double total,
    @Default(OrderStatus.pending) OrderStatus status,
  }) = _Order;

  factory Order.fromJson(Map<String, dynamic> json) => _$OrderFromJson(json);
}

// Usage
final updated = order.copyWith(status: OrderStatus.paid);
```

## Repository Pattern

```dart
abstract class UserRepository {
  Future<User?> findById(String id);
  Future<User> save(User user);
}

@riverpod
UserRepository userRepository(UserRepositoryRef ref) =>
    FirebaseUserRepository(ref.watch(firestoreProvider));
```

## References

See skill: `dart-patterns` for comprehensive Flutter, BLoC, and Riverpod patterns.
