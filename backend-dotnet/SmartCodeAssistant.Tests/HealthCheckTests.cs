using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

namespace SmartCodeAssistant.Tests;

public class HealthCheckTests
{
    [Fact]
    public async Task HealthEndpoint_ReturnsOk()
    {
        // Arrange
        var factory = new WebApplicationFactory<Program>();
        var client = factory.CreateClient();

        // Act
        var response = await client.GetAsync("/health");

        // Assert
        Assert.True(response.IsSuccessStatusCode);
    }

    [Fact]
    public async Task RootEndpoint_ReturnsOk()
    {
        // Arrange
        var factory = new WebApplicationFactory<Program>();
        var client = factory.CreateClient();

        // Act
        var response = await client.GetAsync("/");

        // Assert
        response.EnsureSuccessStatusCode();
        var content = await response.Content.ReadAsStringAsync();
        Assert.Contains("Smart Code Assistant API", content);
    }
}
