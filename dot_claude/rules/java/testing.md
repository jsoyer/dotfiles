---
paths:
  - "**/*.java"
  - "**/Test*.java"
  - "**/*Test.java"
---
# Java Testing

> This file extends [common/testing.md](../common/testing.md) with Java-specific content.

## Test Framework

- **JUnit 5** (Jupiter) for all tests — use `@Test`, `@ParameterizedTest`, `@BeforeEach`
- **Mockito** for mocking dependencies — `@Mock`, `@InjectMocks`, `@ExtendWith(MockitoExtension.class)`
- **AssertJ** for fluent assertions — more readable than JUnit assertions
- **Spring Boot Test** (`@SpringBootTest`, `@WebMvcTest`, `@DataJpaTest`) for integration tests

## Test Organization

```text
src/
├── main/java/com/example/orders/
│   ├── OrderService.java
│   └── OrderRepository.java
└── test/java/com/example/orders/
    ├── OrderServiceTest.java      ← unit test
    ├── OrderRepositoryTest.java   ← @DataJpaTest integration test
    └── OrderControllerTest.java   ← @WebMvcTest slice test
```

## Unit Test Pattern

```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock OrderRepository repo;
    @InjectMocks OrderService service;

    @Test
    void returnsEmptyWhenOrderNotFound() {
        when(repo.findById(any())).thenReturn(Optional.empty());
        assertThat(service.getOrder(UUID.randomUUID())).isEmpty();
    }

    @Test
    void throwsWhenOrderIsNull() {
        assertThatThrownBy(() -> service.place(null))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
```

## Parameterized Tests

```java
@ParameterizedTest
@CsvSource({"alice@example.com, true", "not-an-email, false", ", false"})
void validateEmail(String email, boolean expected) {
    assertThat(EmailValidator.isValid(email)).isEqualTo(expected);
}
```

## Controller Slice Test

```java
@WebMvcTest(OrderController.class)
class OrderControllerTest {
    @Autowired MockMvc mvc;
    @MockBean OrderService service;

    @Test
    void returns404WhenOrderMissing() throws Exception {
        when(service.getOrder(any())).thenReturn(Optional.empty());
        mvc.perform(get("/orders/{id}", UUID.randomUUID()))
           .andExpect(status().isNotFound());
    }
}
```

## Coverage

- Target 80%+ line coverage with JaCoCo
- Configure fail-build threshold in Maven/Gradle

```xml
<!-- maven-jacoco-plugin — fail if below 80% -->
<rule><limits><limit>
  <counter>LINE</counter><value>COVEREDRATIO</value><minimum>0.80</minimum>
</limit></limits></rule>
```

## References

See skill: `java-testing` for Testcontainers, WireMock, and Spring integration test patterns.
