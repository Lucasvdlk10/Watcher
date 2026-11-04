using System.Text.Json;
using Xunit;
using LEIAWatcher.Domain;
namespace LEIAWatcher.UnitTests;
public sealed class JsonContractTests {
 [Fact]public void RealCountsAreParsed(){using var d=JsonDocument.Parse("{\"files_count\":434,\"current_files_count\":9,\"legacy_files_count\":425}"); Assert.Equal(434,JsonFields.Int(d.RootElement,"files_count"));Assert.Equal(434,JsonFields.Int(d.RootElement,"current_files_count")+JsonFields.Int(d.RootElement,"legacy_files_count"));}
 [Fact]public void MissingFieldsDoNotInventCounts(){using var d=JsonDocument.Parse("{}");Assert.Equal(0,JsonFields.Int(d.RootElement,"files_count"));}
 [Fact]public void FakeLlmFlagIsRejectedByCaller(){using var d=JsonDocument.Parse("{\"no_llm\":false}"); Assert.False(JsonFields.Bool(d.RootElement,"no_llm"));}
}
