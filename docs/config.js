// Supabase bağlantı bilgileri.
// Boş bırakılırsa uygulama önce yerel API'yi, o da yoksa tarayıcı
// depolamasını (localStorage) kullanır.
// Not: anon key istemci tarafında kullanılmak üzere tasarlanmıştır,
// herkese açık olması normaldir — veriyi RLS politikaları korur.
window.APP_CONFIG = {
  supabaseUrl: "",     // örn: https://abcdefghijkl.supabase.co
  supabaseAnonKey: "", // Dashboard -> Settings -> API Keys -> anon public
};
