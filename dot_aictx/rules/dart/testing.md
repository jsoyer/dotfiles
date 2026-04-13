---
paths:
  - "**/*.dart"
  - "**/test/**"
  - "**/integration_test/**"
---
# Dart Testing

> This file extends [common/testing.md](../common/testing.md) with Dart-specific content.

## Test Frameworks

- **test** package — unit and integration tests
- **flutter_test** — widget testing (Flutter projects)
- **integration_test** — full app E2E tests on real devices/emulators
- **mockito** with `@GenerateMocks` — mock generation

## Unit Tests

```dart
import 'package:test/test.dart';

void main() {
  group('Email', () {
    test('accepts valid address', () {
      expect('user@example.com'.isValidEmail, isTrue);
    });

    test('rejects address without @', () {
      expect('notanemail'.isValidEmail, isFalse);
    });
  });
}
```

## Widget Tests

```dart
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('UserCard displays name and email', (tester) async {
    await tester.pumpWidget(
      MaterialApp(child: UserCard(user: User(name: 'Alice', email: 'a@b.com'))),
    );
    expect(find.text('Alice'), findsOneWidget);
    expect(find.text('a@b.com'), findsOneWidget);
  });
}
```

## Mockito Mocks

```dart
@GenerateMocks([UserRepository])
import 'user_service_test.mocks.dart';

void main() {
  late MockUserRepository mockRepo;

  setUp(() => mockRepo = MockUserRepository());

  test('returns user when found', () async {
    when(mockRepo.findById('1')).thenAnswer((_) async => User(id: '1', name: 'Alice'));
    final service = UserService(mockRepo);
    final user = await service.getUser('1');
    expect(user.name, 'Alice');
  });
}
```

## Testing Commands

```bash
dart test                        # Unit tests
flutter test                     # Widget tests
flutter test integration_test/   # Integration tests
dart test --coverage=coverage/   # With coverage
```

## References

See skill: `dart-testing` for golden tests, Riverpod testing, and CI setup.
