import os, sys, string, operator

def nhex( name, litle_endian ):
    if litle_endian:
        return nhex( reversed( name ), 0 )
    r = "0x"
    for n in name:
        r += hex( ord( n ) )[ 2: ]
    return r

def cvar( n ):
    return n.replace( "_", "__" ).replace( " ", "_s" ).replace( "\n", "_n" ).replace( "\r", "_r" ).replace( ":", "_d" ).replace( "-", "_m" )

def cstr( n ):
    if n == "\n": return "\\n"
    if n == "\r": return "\\r"
    return n

class Out:
    def __init__( self, f ):
        self.f = f
        self.l = []
        self.s = [] # string that may need to be copied

    def __iadd__( self, line ):
        self.f.write( line + "\n" )
        return self

    def add_cnt( self, c, varo ):
        self.l.append( ( c, varo ) )

    def finalize( self ):
        mvar = {}
        for c, varo in self.l:
            kvar = "mocintc_" + string.join( varo, "__" )
            mvar[ kvar ] = varo
            self += "c_" + c + ": inp_cont = &&l_" + c + "; goto " + kvar + ";"
        for kvar, varo in mvar.items():
            self += kvar + ":"
            for v in varo:
                self += "    " + v + ".make_own_copy_if_not_the_case();"
            self += "    return;"

class Word:
    def __init__( self, word, prob = 1 ):
        self.word = word
        self.prob = prob # unnormalized probability

        
class ParseItem:
    nb_prefix = 0
    
    def __init__( self ):
        self.next = None
        self.fallback = -1
        
    def new_prefix( self ):
        ParseItem.nb_prefix += 1
        return str( ParseItem.nb_prefix ) + "_"
        
    def next_write( self, f, path, varo ):
        if self.next != None:
            self.next.write( f, path, varo )
        else:
            f += "    " + self._fallback( f, path, 0, varo )
        
    def _fallback( self, f, path, beg, varo ):
        if type( self.fallback ) == str:
            return self.fallback
        if beg:
            f.add_cnt( path[ self.fallback ], varo )
            return "{ if ( ++data >= end ) goto c_" + path[ self.fallback ] + "; goto l_" + path[ self.fallback ] + "; }"
        return "goto l_" + path[ self.fallback ] + ";"

class Choice( ParseItem ):
    def __init__( self ):
        ParseItem.__init__( self )
        self.choices = []
        
    def __iadd__( self, word ):
        self.choices.append( word )
        return self
    
    def write( self, f, path = [], varo = [] ):
        p = self.new_prefix()
        self._write_rec( f, p, "", path + [ p ], varo )
        
    def _write_rec( self, f, prefix, beg, path, varo ):
        f += "l_" + prefix + cvar( beg ) + ":"

        for c in self.choices:
            if c.word == beg:
                c.next.write( f, path, varo )
                return

        m = {}
        for c in self.choices:
            if len( c.word ) > len( beg ) and c.word.startswith( beg ):
                l = c.word[ len( beg ) ]
                if l in m: m[ l ] += c.prob
                else:      m[ l ] = c.prob
        k = [ p[ 0 ] for p in sorted( m.iteritems(), key = operator.itemgetter( 1 ), reverse = True ) ]

        for p in reversed( k[ 1: ] ):
            l = prefix + cvar( beg + p )
            f.add_cnt( l, varo )
            f += "    if ( *data == '" + cstr( p ) + "' ) { if ( ++data >= end ) goto c_" + l + "; goto l_" + l + "; }"
        f += "    if ( *data != '" + cstr( k[ 0 ] ) + "' ) " + self._fallback( f, path, len( beg ) == 0, varo )
        l = prefix + cvar( beg + k[ 0 ] )
        f.add_cnt( l, varo )
        f += "    if ( ++data >= end ) goto c_" + l + ";"
 
 
        for p in k:
            self._write_rec( f, prefix, beg + p, path, varo )
            
 
class String( ParseItem ):
    def __init__( self, varname ):
        ParseItem.__init__( self )
        self.varname = varname
        self.next = None
        self.end = ' '
    
    def write( self, f, path = [], varo = [] ):
        l = self.new_prefix()
        f.add_cnt( l + "_cnt", varo + [ self.varname ] )
        endtest = string.join( [ "*data == '" + v + "'" for v in self.end ], " or " )
        f += """
            l_{l}_beg: // first call
                {varname}.data = data;
                while ( true ) {
                    if ( {endtest} ) {
                        {varname}.size = data - {varname}.data;
                        *data = 0;
                        goto e_{l};
                    }
                    if ( ++data == end ) {
                        {varname}.size = data - {varname}.data;
                        goto c_{l}_cnt;
                    }
                }
            l_{l}_cnt: // cont
                while ( true ) {
                    {varname}.make_room_for_at_least_1_char();
                    if ( {endtest} ) {
                        {varname}.data[ {varname}.size ] = 0;
                        goto e_{l};
                    }
                    {varname}.data[ {varname}.size++ ] = *data;
                    if ( ++data == end )
                        goto c_{l}_cnt;
                }

            e_{l}:""". \
            replace( "{l}", l ). \
            replace( "{varname}", self.varname ). \
            replace( "\n            ", "\n" ). \
            replace( "{endtest}", endtest )
        self.next.write( f, path, varo + [ self.varname ] )

class Number( ParseItem ):
    def __init__( self, varname ):
        ParseItem.__init__( self )
        self.varname = varname
    
    def write( self, f, path = [], varo = [] ):
        l = self.new_prefix()
        f.add_cnt( l, varo )
        f += """
            l_{l}:
                if ( *data < '0' or *data > '9' ) goto e_{l};
                {varname} = 10 * {varname} + ( *data - '0' );
                if ( ++data >= end ) goto c_{l};
                goto l_{l};
            e_{l}:""". \
            replace( "{l}", l ). \
            replace( "\n            ", "\n" ). \
            replace( "{varname}", self.varname )
        self.next_write( f, path, varo )

            
class TxtItem( ParseItem ):
    def __init__( self, txt ):
        self.txt = txt
    
    def write( self, f, path, varo ):
        f += self.txt

choice = Choice()
choice.fallback = "goto e_400;"
for req, prob in [ ( "GET ", 5 ), ( "POST ", 3 ), ( "PUT ", 1 ) ]: # , "DELETE ", "TRACE ", "OPTIONS ", "CONNECT ", "HEAD "
    w = Word( req, prob )
    choice += w
    
    s = String( "url" )
    w.next = s

    if req == "POST " or req == "PUT ":
        c = Choice()
        s.next = c
        
        cl = Word( "\nContent-Length: ", 1 )
        c += cl        
        rl = Number( "content_length" )
        cl.next = rl
        
        for ew in [ "\n\n", "\n\r\n" ]:
            en = Word( ew, 1 )
            c += en
            en.next = TxtItem( "    req_" + req[ : -1 ] + "( data, end - data ); return false;" )
    else:
        s.next = TxtItem( "    req_" + req[ : -1 ] + "(); return false;" )

out = Out( file( "src/Celo/HttpRequest_gen.h", "w" ) )
out += "if ( inp_cont )"
out += "    goto *inp_cont;"
out += ""
choice.write( out )
out += ""
out += '#define ERR( NUM, MSG ) e_##NUM: error_##NUM(); return false;'
out += '#include "ErrorCodes.h"'
out += '#undef ERR'
out.finalize()
 
#_:
    #if ( end - data >= 4 ) {
        #int val = *reinterpret_cast<const int *>( data );

        ##if __BYTE_ORDER == __LITTLE_ENDIAN
        #if ( val == 0x4954504f ) { data += 4; goto b_OPTI; }
        #if ( val == 0x20544547 ) { data += 4; goto b_GET_s; }
        #if ( val == 0x454c4544 ) { data += 4; goto b_DELE; }
        #if ( val == 0x43415254 ) { data += 4; goto b_TRAC; }
        #if ( val == 0x20545550 ) { data += 4; goto b_PUT_s; }
        #if ( val == 0x44414548 ) { data += 4; goto b_HEAD; }
        #if ( val == 0x4e4e4f43 ) { data += 4; goto b_CONN; }
        #if ( val == 0x54534f50 ) { data += 4; goto b_POST; }
        ##elif __BYTE_ORDER == __BIG_ENDIAN
        #if ( val == 0x4f505449 ) { data += 4; goto b_OPTI; }
        #if ( val == 0x47455420 ) { data += 4; goto b_GET_s; }
        #if ( val == 0x44454c45 ) { data += 4; goto b_DELE; }
        #if ( val == 0x54524143 ) { data += 4; goto b_TRAC; }
        #if ( val == 0x50555420 ) { data += 4; goto b_PUT_s; }
        #if ( val == 0x48454144 ) { data += 4; goto b_HEAD; }
        #if ( val == 0x434f4e4e ) { data += 4; goto b_CONN; }
        #if ( val == 0x504f5354 ) { data += 4; goto b_POST; }
        ##else
        #Unknown endianness
        ##endif
    #}

    #switch ( *data ) {
    #case 'C': goto a_C;
    #case 'D': goto a_D;
    #case 'G': goto a_G;
    #case 'H': goto a_H;
    #case 'O': goto a_O;
    #case 'P': goto a_P;
    #case 'T': goto a_T;
