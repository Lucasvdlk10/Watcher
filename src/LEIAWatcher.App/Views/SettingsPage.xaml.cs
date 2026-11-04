using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
namespace LEIAWatcher.App.Views;
public sealed partial class SettingsPage:Page {
 public SettingsPage(){InitializeComponent();DataContext=App.State;Loaded+=(s,e)=>{ThemeChoice.SelectedIndex=App.State.Theme=="Alto contraste"?1:0;DensityChoice.SelectedIndex=App.State.Density=="Confortável"?1:0;MotionChoice.SelectedIndex=App.State.Motion=="Completa"?0:App.State.Motion=="Desligada"?2:1;};}
 void ChoicesChanged(object s,SelectionChangedEventArgs e){if(ThemeChoice?.SelectedItem is ComboBoxItem theme)App.State.Theme=theme.Content.ToString()??"Escuro";if(DensityChoice?.SelectedItem is ComboBoxItem density)App.State.Density=density.Content.ToString()??"Compacta";if(MotionChoice?.SelectedItem is ComboBoxItem motion)App.State.Motion=motion.Content.ToString()??"Reduzida";}
 void Save(object s,RoutedEventArgs e){App.State.SavePreferences(); if(App.Main?.Content is FrameworkElement el) el.RequestedTheme=App.State.Theme=="Alto contraste"?ElementTheme.Default:ElementTheme.Dark;}
}
