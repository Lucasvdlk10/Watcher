using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace LEIAWatcher.Domain;

public class Observable : INotifyPropertyChanged
{
 public event PropertyChangedEventHandler? PropertyChanged;
 protected bool Set<T>(ref T field, T value, [CallerMemberName]string name = "") { if (EqualityComparer<T>.Default.Equals(field,value)) return false; field=value; PropertyChanged?.Invoke(this,new(name)); return true; }
 protected void Changed([CallerMemberName]string name = "") => PropertyChanged?.Invoke(this,new(name));
}
public record WatcherRoot(string Id,string Name,string Path,string Mode,string Health,bool Enabled);
public sealed class FileEntry { public string Name {get;set;}=""; public string Path {get;set;}=""; public string Extension {get;set;}=""; public string State {get;set;}=""; public string Source {get;set;}=""; public string Date {get;set;}=""; }
public sealed class AuditEntry { public string Date {get;set;}=""; public string Event {get;set;}=""; public string Outcome {get;set;}=""; public string Detail {get;set;}=""; }
public sealed class RuleEntry : Observable {
 public string Id {get;set;}=Guid.NewGuid().ToString("N")[..10];
 string kind="type", values="",target="Outros";
 public string Kind {get=>kind;set=>Set(ref kind,value);} public string Values {get=>values;set=>Set(ref values,value);} public string Target {get=>target;set=>Set(ref target,value);}
 public bool Enabled {get;set;}=true;
}
public static class JsonFields {
 public static string Str(JsonElement obj, string key, string fallback="") => obj.ValueKind==JsonValueKind.Object && obj.TryGetProperty(key,out var v) && v.ValueKind!=JsonValueKind.Null ? v.ToString() : fallback;
 public static int Int(JsonElement obj,string key) => int.TryParse(Str(obj,key),out var n)?n:0;
 public static bool Bool(JsonElement obj,string key) => bool.TryParse(Str(obj,key),out var n)&&n;
 public static JsonElement Array(JsonElement obj,string key) => obj.ValueKind==JsonValueKind.Object && obj.TryGetProperty(key,out var v)&&v.ValueKind==JsonValueKind.Array?v:JsonDocument.Parse("[]").RootElement;
}
